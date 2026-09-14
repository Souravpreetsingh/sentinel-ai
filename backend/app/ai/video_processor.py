"""Orchestrates the full video analysis pipeline: read → detect → track → rules.

The video processor is agnostic to delivery mechanism (HTTP upload, live
stream, background task). It depends only on the detector abstraction and the
tracker/zone/event engines.

When running in a background thread the processor supports:
  - configurable frame skipping (AI_PROCESS_EVERY_N_FRAMES)
  - debug-frame export (AI_DEBUG → uploads/debug/)
  - optional annotated output video (GENERATE_OUTPUT_VIDEO → uploads/processed/)
  - progress / detection / event callbacks consumed by the job runner
  - per-frame performance metrics
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import cv2  # type: ignore
import numpy as np  # type: ignore

from app.ai.annotate import annotate_frame
from app.ai.detector import ObjectDetector
from app.ai.events import EventEngine
from app.ai.tracker import TrackerRegistry, TrackedObject
from app.ai.types import DetectionEvent
from app.ai.zones import Zone, ZoneAnalyzer
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("ai.video_processor")


class FrameResult:
    __slots__ = (
        "frame_index", "detections", "tracked", "people_count",
        "events", "timestamp", "inference_ms",
    )

    def __init__(
        self,
        frame_index: int,
        detections: list,
        tracked: list[TrackedObject],
        people_count: int,
        events: list[DetectionEvent],
        timestamp: datetime,
        inference_ms: float = 0.0,
    ):
        self.frame_index = frame_index
        self.detections = detections
        self.tracked = tracked
        self.people_count = people_count
        self.events = events
        self.timestamp = timestamp
        self.inference_ms = inference_ms


class VideoProcessor:
    def __init__(
        self,
        detector: ObjectDetector,
        settings: Settings | None = None,
    ) -> None:
        self.detector = detector
        self.settings = settings or get_settings()
        self._trackers = TrackerRegistry()
        self._engine = EventEngine(
            cooldown_seconds=self.settings.event_cooldown_seconds,
        )
        self._frame_skip = max(1, int(self.settings.ai_process_every_n_frames))

    @property
    def engine(self) -> EventEngine:
        return self._engine

    def set_zones(self, zones: list[Zone]) -> None:
        self._engine.set_zones(zones)

    def reset(self, camera_id: str | None = None) -> None:
        self._trackers.reset(camera_id)
        for analyzer in (
            self._engine.crowd,
            self._engine.abandoned,
            self._engine.stopped,
            self._engine.fall,
            self._engine.traffic,
        ):
            if hasattr(analyzer, "reset"):
                analyzer.reset()

    # ------------------------------------------------------------------
    # Single-frame processing
    # ------------------------------------------------------------------

    def process_frame(
        self,
        frame: Any,
        camera_id: str | None = None,
        frame_index: int = 0,
        timestamp: datetime | None = None,
    ) -> FrameResult:
        ts = timestamp or datetime.now(timezone.utc)
        detections = self.detector.detect(frame)
        tracker = self._trackers.get(camera_id)
        tracked = tracker.update(detections, ts)
        zone_events = self._engine.zone_analyzer.update(camera_id, tracked, ts)
        people_count = sum(1 for t in tracked if t.category == "person")
        events = self._engine.run(
            camera_id=camera_id,
            tracked=tracked,
            timestamp=ts,
            zone_events=zone_events,
            people_count=people_count,
        )
        return FrameResult(
            frame_index=frame_index,
            detections=detections,
            tracked=tracked,
            people_count=people_count,
            events=events,
            timestamp=ts,
        )

    # ------------------------------------------------------------------
    # Full video file processing (runs in a background thread)
    # ------------------------------------------------------------------

    def process_file(
        self,
        video_path: Path,
        camera_id: str | None = None,
        job_id: str | None = None,
        on_progress: Callable[[dict[str, Any]], None] | None = None,
        on_detection: Callable[[dict[str, Any]], None] | None = None,
        on_event: Callable[[DetectionEvent, np.ndarray], None] | None = None,
    ) -> dict[str, Any]:
        """Process an entire video file and return aggregate results.

        Parameters
        ----------
        on_progress:
            Called periodically with ``{"frame", "total_frames", "progress", "fps"}``.
        on_detection:
            Called per processed frame with the realtime ``detection`` payload
            (WebSocket spec format).
        on_event:
            Called once for every cooldown-passed detection event. The second
            argument is the *original* (undecorated) BGR frame so callers can
            save a snapshot for incident evidence.

        This function is CPU/GPU-bound and **must** be called from a background
        thread or executor, never directly in the FastAPI event loop.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / source_fps if source_fps > 0 else 0.0

        # Optional annotated output video writer.
        writer: cv2.VideoWriter | None = None
        if self.settings.generate_output_video:
            out_dir = self.settings.processed_video_path()
            out_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{(job_id or 'anon')}-processed.mp4"
            out_path = out_dir / out_name
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_path), fourcc, source_fps, (width, height))
            logger.info("Writing annotated output video → %s", out_path)

        # Debug frame directory.
        debug_dir: Path | None = None
        if self.settings.ai_debug:
            debug_dir = self.settings.debug_path()
            debug_dir.mkdir(parents=True, exist_ok=True)

        inference_times: list[float] = []
        processed = 0
        skipped = 0
        total_events = 0
        total_detections = 0
        all_events: list[dict] = []
        all_detections: list[dict] = []
        t_start = time.monotonic()

        frame_index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % self._frame_skip != 0:
                skipped += 1
                frame_index += 1
                continue

            ts = datetime.now(timezone.utc)
            t_inf = time.monotonic()
            result = self.process_frame(
                frame,
                camera_id=camera_id,
                frame_index=frame_index,
                timestamp=ts,
            )
            inf_ms = (time.monotonic() - t_inf) * 1000.0
            inference_times.append(inf_ms)

            people = sum(1 for d in result.tracked if d.category == "person")
            vehicles = sum(1 for d in result.tracked if d.category == "vehicle")

            # Broadcast detection payload (WebSocket spec format).
            if on_detection is not None:
                det_payload = {
                    "event": "detection",
                    "video_id": job_id,
                    "camera_id": camera_id,
                    "timestamp": ts.isoformat(),
                    "frame_number": frame_index,
                    "objects": [
                        {
                            "track_id": obj.track_id,
                            "class_name": obj.class_name,
                            "confidence": round(obj.confidence, 3),
                            "bbox": {
                                "x1": round(obj.x1, 1),
                                "y1": round(obj.y1, 1),
                                "x2": round(obj.x2, 1),
                                "y2": round(obj.y2, 1),
                            },
                        }
                        for obj in result.tracked
                    ],
                }
                try:
                    on_detection(det_payload)
                except Exception:  # pragma: no cover
                    pass

            # Emit cooldown-limited events → callers create incidents + snapshots.
            for evt in result.events:
                all_events.append(evt.to_dict())
                if on_event is not None:
                    try:
                        on_event(evt, frame)
                    except Exception:  # pragma: no cover
                        pass

            for det in result.detections:
                all_detections.append(det.to_dict())

            processed += 1

            # Debug frame export (every Nth processed frame).
            if debug_dir is not None and processed % max(1, self.settings.debug_frame_every_n) == 0:
                try:
                    annotated = annotate_frame(
                        frame,
                        tracked=result.tracked,
                        zones=self._engine.zones.enabled_zones(),
                        events=result.events,
                        label_lines=[
                            f"Frame {frame_index}  People {people}  Vehicles {vehicles}",
                            f"Inference {inf_ms:.1f}ms  Processor {camera_id or 'N/A'}",
                        ],
                    )
                    debug_path = debug_dir / f"f{frame_index:06d}.jpg"
                    cv2.imwrite(str(debug_path), annotated)
                except Exception:  # pragma: no cover
                    logger.debug("Debug frame write failed", exc_info=True)

            # Annotated output video frame.
            if writer is not None:
                try:
                    annotated = annotate_frame(
                        frame,
                        tracked=result.tracked,
                        zones=self._engine.zones.enabled_zones(),
                        events=result.events,
                    )
                    writer.write(annotated)
                except Exception:  # pragma: no cover
                    pass

            # Progress callback.
            progress = min(99.0, (frame_index / max(1, total_frames)) * 100.0) if total_frames > 0 else 0.0
            elapsed = time.monotonic() - t_start
            fps = processed / elapsed if elapsed > 0 else 0.0
            if on_progress is not None:
                try:
                    on_progress({
                        "frame": frame_index,
                        "total_frames": total_frames,
                        "progress": round(progress, 1),
                        "fps": round(fps, 1),
                    })
                except Exception:  # pragma: no cover
                    pass

            frame_index += 1

        cap.release()
        if writer is not None:
            writer.release()

        elapsed = time.monotonic() - t_start
        avg_inference = sum(inference_times) / len(inference_times) if inference_times else 0.0

        # Final 100% progress signal.
        if on_progress is not None:
            try:
                on_progress({
                    "frame": total_frames,
                    "total_frames": total_frames,
                    "progress": 100.0,
                    "fps": round(processed / elapsed, 1) if elapsed > 0 else 0.0,
                })
            except Exception:  # pragma: no cover
                pass

        return {
            "total_frames": total_frames,
            "frames_processed": processed,
            "frames_skipped": skipped,
            "duration_seconds": round(duration, 2),
            "processing_time_seconds": round(elapsed, 2),
            "fps_throughput": round(processed / elapsed, 2) if elapsed > 0 else 0,
            "source_fps": round(source_fps, 1),
            "average_inference_ms": round(avg_inference, 2),
            "people_detected": sum(
                1 for det in all_detections if det.get("raw_class_name") == "person"
            ),
            "vehicles_detected": sum(
                1 for det in all_detections if det.get("raw_class_name") in ("car", "truck", "bus", "motorcycle", "bicycle")
            ),
            "events_count": len(all_events),
            "detections_count": len(all_detections),
            "events": all_events,
            "sample_detections": all_detections[:200],
            "output_video": str(self.settings.processed_video_path() / f"{job_id}-processed.mp4") if self.settings.generate_output_video else None,
        }