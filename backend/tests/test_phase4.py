"""Phase 4 tests: traffic rule, cooldown dedup, zone model, incident generation,
video job lifecycle, frame skipping, annotation, YOLO device selection.
"""

from __future__ import annotations

import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.ai.tracker import TrackedObject


def _make_tracked(class_name: str, track_id: str, x1: float = 10, y1: float = 10,
                  x2: float = 50, y2: float = 50, confidence: float = 0.9) -> TrackedObject:
    return TrackedObject(
        track_id=track_id, class_name=class_name, category="vehicle" if class_name != "person" else "person",
        confidence=confidence, x1=x1, y1=y1, x2=x2, y2=y2,
        first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
        last_moved_at=datetime.now(timezone.utc),
    )


# ── Traffic Congestion ────────────────────────────────────────────────

class TestTrafficCongestion:
    def test_density_calculation(self):
        from app.ai.traffic import TrafficCongestionAnalyzer
        ta = TrafficCongestionAnalyzer(threshold=0.5, capacity=6, min_vehicles=1)
        tracked = [_make_tracked("car", f"v{i}") for i in range(3)]
        assert ta.density(tracked) == pytest.approx(0.5)

    def test_no_event_below_threshold(self):
        from app.ai.traffic import TrafficCongestionAnalyzer
        ta = TrafficCongestionAnalyzer(threshold=0.75, capacity=6, min_vehicles=3)
        tracked = [_make_tracked("car", f"v{i}") for i in range(3)]
        ts = datetime.now(timezone.utc)
        assert ta.evaluate("cam-1", tracked, ts) is None

    def test_emits_event_above_threshold(self):
        from app.ai.traffic import TrafficCongestionAnalyzer
        ta = TrafficCongestionAnalyzer(threshold=0.5, capacity=6, min_vehicles=3)
        tracked = [_make_tracked("car", f"v{i}") for i in range(4)]
        ts = datetime.now(timezone.utc)
        evt = ta.evaluate("cam-1", tracked, ts)
        assert evt is not None
        assert evt.event_type == "traffic_congestion"
        assert evt.severity == "medium"
        assert len(evt.objects) == 4

    def test_min_vehicles_filter(self):
        from app.ai.traffic import TrafficCongestionAnalyzer
        ta = TrafficCongestionAnalyzer(threshold=0.1, capacity=6, min_vehicles=5)
        tracked = [_make_tracked("car", f"v{i}") for i in range(3)]
        ts = datetime.now(timezone.utc)
        assert ta.evaluate("cam-1", tracked, ts) is None

    def test_ignores_people(self):
        from app.ai.traffic import TrafficCongestionAnalyzer
        ta = TrafficCongestionAnalyzer(threshold=0.1, capacity=6, min_vehicles=1)
        tracked = [_make_tracked("person", f"p{i}") for i in range(5)]
        ts = datetime.now(timezone.utc)
        assert ta.evaluate("cam-1", tracked, ts) is None


# ── Cooldown Dedup ───────────────────────────────────────────────────

class TestEventCooldown:
    def test_cooldown_suppresses_duplicate(self):
        from app.ai.events import EventEngine
        engine = EventEngine(cooldown_seconds=60)
        ts = datetime.now(timezone.utc)
        crowd_tracker = [_make_tracked("person", f"p{i}") for i in range(35)]
        engine.crowd._recent = {}

        events1 = engine.process_crowd("cam-1", 35, ts)
        assert len(events1) == 1

        ts2 = datetime.now(timezone.utc)
        events2 = engine.process_crowd("cam-1", 35, ts2)
        assert len(events2) == 0

    def test_cooldown_allows_after_expiry(self):
        from app.ai.events import EventEngine
        engine = EventEngine(cooldown_seconds=0.01)
        ts = datetime.now(timezone.utc)
        engine.crowd._recent = {}

        events1 = engine.process_crowd("cam-1", 35, ts)
        assert len(events1) == 1

        time.sleep(0.02)
        ts2 = datetime.now(timezone.utc)
        events2 = engine.process_crowd("cam-1", 35, ts2)
        assert len(events2) == 1

    def test_different_cameras_independent_cooldown(self):
        from app.ai.events import EventEngine
        engine = EventEngine(cooldown_seconds=999)
        ts = datetime.now(timezone.utc)
        engine.crowd._recent = {}

        events1 = engine.process_crowd("cam-1", 35, ts)
        assert len(events1) == 1

        events2 = engine.process_crowd("cam-2", 35, ts)
        assert len(events2) == 1


# ── Zone Model ───────────────────────────────────────────────────────

class TestZoneModel:
    def test_zone_auto_id_from_name(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="Parking Lot A", points=(Point(0, 0), Point(100, 0), Point(100, 100)))
        assert z.id == "parking-lot-a"

    def test_zone_explicit_id_preserved(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="My Zone", points=(Point(0, 0), Point(100, 0), Point(100, 100)), id="custom-id")
        assert z.id == "custom-id"

    def test_zone_type_restricted(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="R", points=(Point(0, 0), Point(100, 0), Point(100, 100)), zone_type="restricted")
        assert z.zone_type == "restricted"
        assert z.type == "restricted"
        assert z.event_type == "restricted_zone_entry"

    def test_zone_type_monitoring(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="M", points=(Point(0, 0), Point(100, 0), Point(100, 100)), zone_type="monitoring")
        assert z.event_type == "zone_presence"

    def test_zone_type_traffic(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="T", points=(Point(0, 0), Point(100, 0), Point(100, 100)), zone_type="traffic")
        assert z.event_type == "zone_vehicle_entry"

    def test_zone_to_dict(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="Test", points=(Point(10, 20), Point(30, 40), Point(50, 60)), zone_type="restricted")
        d = z.to_dict()
        assert d["id"] == "test"
        assert d["type"] == "restricted"
        assert d["enabled"] is True
        assert d["polygon"] == [[10, 20], [30, 40], [50, 60]]

    def test_zone_disabled(self):
        from app.ai.zones import Zone, Point, ZoneAnalyzer
        z = Zone(name="D", points=(Point(0, 0), Point(100, 0), Point(100, 100)), enabled=False)
        za = ZoneAnalyzer(zones=[z])
        assert za.enabled_zones() == []

    def test_zone_contains_bbox_center(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="R", points=(Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)))
        assert z.contains_bbox(40, 40, 60, 60) is True
        assert z.contains_bbox(200, 200, 300, 300) is False

    def test_zone_points_coercion(self):
        from app.ai.zones import Zone, Point
        z = Zone(name="C", points=[(10, 20), (30, 40), (50, 60)])
        assert all(isinstance(p, Point) for p in z.points)


# ── Incident Generation from Events ──────────────────────────────────

class TestIncidentGeneration:
    def test_create_from_event(self, db):
        from app.services import incident_service
        from app.ai.types import DetectionEvent
        evt = DetectionEvent(
            event_id="test-evt-001",
            event_type="restricted_zone_entry",
            severity="high",
            camera_id="cam-1",
            timestamp=datetime.now(timezone.utc),
            confidence=0.95,
            objects=[{"class_name": "person", "track_id": "t1"}],
            metadata={"zone": "lobby"},
        )
        inc = incident_service.create_from_event(db, evt)
        assert inc is not None
        assert inc.type == "restricted_zone_entry"
        assert inc.severity == "high"
        assert inc.camera_id == "cam-1"
        assert inc.confidence == 0.95
        assert inc.status == "open"
        assert inc.assigned_to is None
        assert inc.id.startswith("INC-")

    def test_create_from_event_metadata(self, db):
        from app.services import incident_service
        from app.ai.types import DetectionEvent
        evt = DetectionEvent(
            event_id="test-evt-002",
            event_type="crowd_density_high",
            severity="medium",
            camera_id="cam-2",
            timestamp=datetime.now(timezone.utc),
            confidence=0.80,
            objects=[],
            metadata={"people_count": 42},
        )
        inc = incident_service.create_from_event(db, evt)
        assert inc is not None
        assert inc.metadata_json is not None
        assert inc.metadata_json.get("source") == "ai.video_pipeline"
        assert inc.metadata_json.get("people_count") == 42


# ── Video Job Lifecycle ──────────────────────────────────────────────

class TestVideoJobLifecycle:
    def _create_synthetic_video(self, path: Path, frames: int = 5, fps: float = 10.0) -> None:
        """Create a small synthetic MP4 with OpenCV."""
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, fps, (320, 240))
        for i in range(frames):
            frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            writer.write(frame)
        writer.release()

    def test_upload_and_status(self, client):
        content = b"\x00" * 50
        resp = client.post(
            "/api/video/upload",
            files={"file": ("test.mp4", __import__("io").BytesIO(content), "video/mp4")},
        )
        assert resp.status_code == 201
        vid = resp.json()["video_id"]
        resp = client.get(f"/api/video/{vid}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("queued", "processing", "completed", "failed")
        assert "frames_total" in body
        assert "detections_count" in body

    def test_job_with_camera_id(self, client):
        content = b"\x00" * 50
        resp = client.post(
            "/api/video/upload",
            files={
                "file": ("test.mp4", __import__("io").BytesIO(content), "video/mp4"),
                "camera_id": ("", "cam-1", "text/plain"),
            },
        )
        assert resp.status_code == 201
        vid = resp.json()["video_id"]
        resp = client.get(f"/api/video/{vid}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("camera_id") == "cam-1"

    def test_real_video_processing(self, db):
        from app.services import job_runner
        from app.models import VideoJob
        from app.core.config import get_settings

        tmp = Path(tempfile.mkdtemp())
        video = tmp / "test.mp4"
        self._create_synthetic_video(video, frames=6, fps=10.0)

        job = VideoJob(
            id="job-test-001",
            video_id="vid-001",
            camera_id=None,
            original_filename="test.mp4",
            stored_path=str(video),
            file_size=video.stat().st_size,
            status="queued",
            progress=0.0,
            frames_total=0,
            frames_processed=0,
            fps=0.0,
            detections_count=0,
            events_count=0,
        )
        db.add(job)
        db.commit()

        settings = get_settings()
        job_runner.process_job_sync("job-test-001", settings)

        db.refresh(job)
        assert job.status == "completed"
        assert job.frames_total > 0
        assert job.frames_processed > 0
        assert job.fps > 0
        assert job.completed_at is not None
        assert job.result is not None
        assert "total_frames" in job.result

    def test_job_failure_on_missing_file(self, db):
        from app.services import job_runner
        from app.models import VideoJob
        from app.core.config import get_settings

        job = VideoJob(
            id="job-missing-001",
            video_id="vid-missing",
            camera_id=None,
            original_filename="missing.mp4",
            stored_path="/nonexistent/path/video.mp4",
            file_size=0,
            status="queued",
            progress=0.0,
            frames_total=0,
            frames_processed=0,
            fps=0.0,
            detections_count=0,
            events_count=0,
        )
        db.add(job)
        db.commit()

        settings = get_settings()
        job_runner.process_job_sync("job-missing-001", settings)

        db.refresh(job)
        assert job.status == "failed"
        assert job.error is not None

    def test_job_failure_on_empty_video(self, db):
        from app.services import job_runner
        from app.models import VideoJob
        from app.core.config import get_settings

        tmp = Path(tempfile.mkdtemp())
        video = tmp / "empty.mp4"
        video.write_bytes(b"\x00" * 100)

        job = VideoJob(
            id="job-empty-001",
            video_id="vid-empty",
            camera_id=None,
            original_filename="empty.mp4",
            stored_path=str(video),
            file_size=100,
            status="queued",
            progress=0.0,
            frames_total=0,
            frames_processed=0,
            fps=0.0,
            detections_count=0,
            events_count=0,
        )
        db.add(job)
        db.commit()

        settings = get_settings()
        job_runner.process_job_sync("job-empty-001", settings)

        db.refresh(job)
        assert job.status == "failed"
        assert job.error is not None


# ── Frame Skipping ───────────────────────────────────────────────────

class TestFrameSkipping:
    def test_frame_skip_ratio(self):
        from app.ai.video_processor import VideoProcessor
        from app.ai.mock import MockObjectDetector
        from app.core.config import Settings

        settings = Settings(ai_process_every_n_frames=3)
        proc = VideoProcessor(detector=MockObjectDetector(seed=42), settings=settings)
        assert proc._frame_skip == 3


# ── Annotation ───────────────────────────────────────────────────────

class TestAnnotation:
    def test_annotate_frame_returns_same_shape(self):
        from app.ai.annotate import annotate_frame
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = annotate_frame(frame)
        assert result.shape == frame.shape

    def test_annotate_with_zones(self):
        from app.ai.annotate import annotate_frame
        from app.ai.zones import Zone, Point
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        zones = [Zone(name="TestZone", points=(Point(10, 10), Point(100, 10), Point(100, 100), Point(10, 100)))]
        result = annotate_frame(frame, zones=zones)
        assert result.shape == frame.shape
        assert not np.array_equal(result, frame)

    def test_annotate_with_tracked_objects(self):
        from app.ai.annotate import annotate_frame
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        tracked = [_make_tracked("person", "p1", 20, 20, 60, 80)]
        result = annotate_frame(frame, tracked=tracked)
        assert result.shape == frame.shape


# ── YOLO Device Selection ────────────────────────────────────────────

class TestYoloDeviceSelection:
    def test_select_device_empty_string(self):
        from app.ai.yolo import select_device
        dev = select_device("")
        assert dev in ("cpu", "cuda", "cuda:0", "mps")

    def test_select_device_explicit_cpu(self):
        from app.ai.yolo import select_device
        dev = select_device("cpu")
        assert dev == "cpu"

    def test_dependency_status_returns_string(self):
        from app.ai.yolo import dependency_status
        status = dependency_status()
        assert isinstance(status, str)


# ── Evidence Snapshot ────────────────────────────────────────────────

class TestEvidenceSnapshot:
    def test_save_snapshot(self, db):
        from app.services.evidence_service import save_snapshot
        frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        ev = save_snapshot(db, frame, incident_id="INC-1001", camera_id="cam-1", title="Test snap")
        assert ev is not None
        assert ev.type == "snapshot"
        assert ev.file_path.endswith(".jpg")
        assert ev.hash is not None
        assert len(ev.hash) == 64

    def test_save_snapshot_none_frame(self, db):
        from app.services.evidence_service import save_snapshot
        assert save_snapshot(db, None) is None

    def test_save_snapshot_empty_frame(self, db):
        from app.services.evidence_service import save_snapshot
        assert save_snapshot(db, np.array([])) is None
