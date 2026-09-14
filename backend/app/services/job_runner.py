"""Background job runner for video analysis jobs.

Polls the database for queued jobs and processes them off the event loop.
Each job runs the real pipeline (detect → track → rules) and:
  - streams ``video_progress`` / ``detection`` / ``event_created`` over WebSocket
  - creates Incidents + snapshot Evidence from cooldown-limited events
  - persists processing metrics on the VideoJob row
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.ai.factory import build_detector
from app.ai.types import DetectionEvent
from app.ai.video_processor import VideoProcessor
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.runtime import broadcast_threadsafe, runtime
from app.core.database import get_session_factory
from app.services import incident_service
from app.services import evidence_service
from app.services.system_service import update_video_metrics

logger = get_logger("worker.job_runner")

RUNNING = True


def process_job_sync(job_id: str, settings: Settings) -> None:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        from app.models import Camera, Detection, VideoJob

        job = session.query(VideoJob).filter(VideoJob.id == job_id).first()
        if job is None:
            logger.error("Job %s not found", job_id)
            return

        claimed = session.execute(
            text(
                "UPDATE video_jobs SET status = 'processing', started_at = datetime('now') "
                "WHERE id = :job_id AND status IN ('queued', 'failed')"
            ),
            {"job_id": job_id},
        ).rowcount
        session.commit()
        if claimed == 0:
            logger.info("Job %s already claimed or completed; skipping", job_id)
            return
        session.refresh(job)

        camera = None
        if job.camera_id:
            camera = session.query(Camera).filter(Camera.id == job.camera_id).first()

        def broadcast_progress(p: dict[str, Any]) -> None:
            job.progress = p.get("progress", 0.0)
            job.frames_total = int(p.get("total_frames", 0))
            job.frames_processed = int(p.get("frame", 0))
            job_version = {
                "event": "video_progress",
                "video_id": job.video_id,
                "frame": p.get("frame", 0),
                "total_frames": p.get("total_frames", 0),
                "progress": p.get("progress", 0.0),
                "fps": p.get("fps", 0.0),
            }
            broadcast_threadsafe(job_version.pop("event"), job_version)

        pending_detections: list[Detection] = []

        def broadcast_detection(payload: dict[str, Any]) -> None:
            broadcast_threadsafe(payload["event"], payload)
            ts_raw = payload.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
            except (TypeError, ValueError):
                ts = datetime.now(timezone.utc)
            for obj in payload.get("objects") or []:
                box = obj.get("bbox") or {}
                cls_name = str(obj.get("class_name", "unknown"))[:32]
                pending_detections.append(
                    Detection(
                        id=uuid.uuid4().hex,
                        camera_id=payload.get("camera_id") or job.camera_id,
                        video_job_id=job.id,
                        class_name=cls_name,
                        confidence=float(obj.get("confidence", 0.0) or 0.0),
                        x1=float(box.get("x1", 0.0) or 0.0),
                        y1=float(box.get("y1", 0.0) or 0.0),
                        x2=float(box.get("x2", 0.0) or 0.0),
                        y2=float(box.get("y2", 0.0) or 0.0),
                        track_id=str(obj.get("track_id") or "")[:32] or None,
                        source=payload.get("source", "file"),
                        detected_at=ts,
                    )
                )

        def handle_event(evt: DetectionEvent, frame) -> None:
            # Incidents already deduped by EVENT_COOLDOWN_SECONDS.
            inc = incident_service.create_from_event(session, evt, camera=camera)
            if inc is not None:
                evidence_service.save_snapshot(
                    session,
                    frame,
                    incident_id=inc.id,
                    camera_id=evt.camera_id,
                    title=f"AI capture - {evt.event_type}",
                )
            broadcast_threadsafe("event_created", {
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "severity": evt.severity,
                "camera_id": evt.camera_id,
                "timestamp": evt.timestamp.isoformat(),
                "confidence": evt.confidence,
                "metadata": evt.metadata or {},
            })

        try:
            detector = build_detector(settings)
            processor = VideoProcessor(detector, settings)
            video_path = Path(job.stored_path)

            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {job.stored_path}")

            # Fail fast on unreadable / empty files.
            import cv2  # type: ignore

            probe = cv2.VideoCapture(str(video_path))
            if not probe.isOpened():
                raise RuntimeError(f"Invalid or unsupported video file: {video_path.name}")
            total = int(probe.get(cv2.CAP_PROP_FRAME_COUNT))
            probe.release()
            if total <= 0:
                raise RuntimeError("Video has no readable frames (empty or corrupted).")

            result = processor.process_file(
                video_path,
                camera_id=job.camera_id,
                job_id=job.id,
                on_progress=broadcast_progress,
                on_detection=broadcast_detection,
                on_event=handle_event,
            )

            job.status = "completed"
            job.progress = 100.0
            job.completed_at = datetime.now(timezone.utc)
            job.result = result
            job.frames_total = int(result.get("total_frames", total))
            job.frames_processed = int(result.get("frames_processed", 0))
            job.fps = float(result.get("fps_throughput", 0.0))
            job.detections_count = int(result.get("detections_count", 0))
            job.events_count = int(result.get("events_count", 0))
            if pending_detections:
                session.add_all(pending_detections)
            session.commit()
            update_video_metrics(result)

            broadcast_threadsafe("video_progress", {
                "video_id": job.video_id,
                "frame": job.frames_total,
                "total_frames": job.frames_total,
                "progress": 100.0,
                "fps": job.fps,
            })
            logger.info("Job %s completed (frames=%d detections=%d events=%d)",
                        job_id, job.frames_processed, job.detections_count, job.events_count)

        except Exception as exc:
            if job is not None:
                from app.core.security import sanitize_error_message

                job.status = "failed"
                job.error = sanitize_error_message(exc)
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                update_video_metrics({}, failed=True)
                broadcast_threadsafe("video_progress", {
                    "video_id": job.video_id,
                    "status": "failed",
                    "error": job.error,
                })
            logger.warning("Job %s failed: %s", job_id, exc, exc_info=True)

    except Exception as outer_exc:
        # Never let a job crash the worker loop / API process.
        logger.error("Unhandled failure while processing job %s: %s", job_id, outer_exc, exc_info=True)
    finally:
        session.close()


async def worker_loop(poll_seconds: float = 1.0) -> None:
    session_factory = get_session_factory()
    while RUNNING:
        session = session_factory()
        try:
            from app.models import VideoJob
            queued = session.query(VideoJob).filter(VideoJob.status == "queued").all()
            for job in queued:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(
                    runtime.executor,
                    process_job_sync,
                    job.id,
                    get_settings(),
                )
        except Exception as exc:
            logger.error("Worker poll error: %s", exc)
        finally:
            session.close()
        await asyncio.sleep(poll_seconds)