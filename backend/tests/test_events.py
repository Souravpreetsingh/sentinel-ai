"""Event engine + crowd / abandoned / vehicle-stopped / fall tests."""

from datetime import datetime, timedelta, timezone

from app.ai.abandoned import AbandonedObjectDetector
from app.ai.crowd import CrowdAnalyzer
from app.ai.events import (
    ABANDONED_OBJECT,
    CROWD_DENSITY_HIGH,
    EVENT_SEVERITIES,
    PERSON_FALLEN,
    VEHICLE_STOPPED,
    EventEngine,
)
from app.ai.fall import FallDetector
from app.ai.tracker import Tracker, TrackedObject
from app.ai.vehicle_stopped import VehicleStoppedDetector


def _make_tracked(
    track_id: str,
    class_name: str,
    category: str = "person",
    x1: float = 100.0,
    y1: float = 100.0,
    x2: float = 200.0,
    y2: float = 300.0,
    stationary: float = 0.0,
    age: float = 5.0,
    history: list | None = None,
) -> TrackedObject:
    now = datetime.now(timezone.utc)
    ts = now
    if stationary > 0:
        last_moved = now - timedelta(seconds=stationary)
    else:
        last_moved = now
    return TrackedObject(
        track_id=track_id,
        class_name=class_name,
        category=category,
        confidence=0.9,
        x1=x1, y1=y1, x2=x2, y2=y2,
        first_seen=now - timedelta(seconds=age) if age else now,
        last_seen=now,
        last_moved_at=last_moved,
        frame_count=int(age / 0.033),
        history=history if history is not None else [
            ((x1 + x2) / 2, (y1 + y2) / 2, abs(y2 - y1) / max(abs(x2 - x1), 1))
        ],
    )


def test_crowd_low():
    a = CrowdAnalyzer(low_max=15, medium_max=30)
    assert a.classify(0) == "LOW"
    assert a.classify(15) == "LOW"
    assert a.classify(16) == "MEDIUM"
    assert a.classify(30) == "MEDIUM"
    assert a.classify(31) == "HIGH"
    assert a.evaluate(None, 10, datetime.now(timezone.utc)) is None


def test_crowd_high():
    a = CrowdAnalyzer()
    now = datetime.now(timezone.utc)
    result = a.evaluate(None, 35, now)
    assert result is not None
    assert result.event_type == CROWD_DENSITY_HIGH
    assert result.severity == "high"
    assert result.metadata["people_count"] == 35
    assert EVENT_SEVERITIES[PERSON_FALLEN] == "high"


def test_abandoned_object():
    det = AbandonedObjectDetector(stationary_seconds=5.0, object_classes=("bag",))
    now = datetime.now(timezone.utc)
    obj = _make_tracked("OBJECT#001", "bag", category="person", x1=50, y1=50, x2=100, y2=100, stationary=10.0)
    event = det.evaluate("CAM-01", [obj], now)
    assert event is not None
    assert event.event_type == ABANDONED_OBJECT
    # Same object should not trigger again (reported set).
    assert det.evaluate("CAM-01", [obj], now) is None
    det.reset()
    assert det.evaluate("CAM-01", [obj], now) is not None


def test_abandoned_not_with_nearby_person():
    det = AbandonedObjectDetector(stationary_seconds=1.0, object_classes=("bag",))
    now = datetime.now(timezone.utc)
    bag = _make_tracked("OBJ#1", "bag", x1=100, y1=100, x2=130, y2=130, stationary=10.0)
    person = _make_tracked("P#1", "person", category="person", x1=110, y1=110, x2=160, y2=250)
    event = det.evaluate(None, [bag, person], now)
    assert event is None


def test_vehicle_stopped():
    det = VehicleStoppedDetector(stationary_seconds=5.0)
    now = datetime.now(timezone.utc)
    car = _make_tracked("V#1", "car", category="vehicle", stationary=15.0)
    event = det.evaluate("CAM-04", [car], now)
    assert event is not None
    assert event.event_type == VEHICLE_STOPPED


def test_vehicle_not_stopped():
    det = VehicleStoppedDetector(stationary_seconds=20.0)
    now = datetime.now(timezone.utc)
    car = _make_tracked("V#2", "car", category="vehicle", stationary=2.0)
    assert det.evaluate(None, [car], now) is None


def test_fall_detector_signals():
    det = FallDetector(velocity_threshold=5.0)
    now = datetime.now(timezone.utc)
    history = []
    for i in range(10):
        aspect = 1.8 if i < 5 else 0.7
        history.append((200.0, float(150 + i * 5), aspect))
    person = _make_tracked(
        "P#2", "person", x1=150, y1=200, x2=250, y2=215,
        stationary=0, age=6.0, history=history,
    )
    person.last_seen = now
    event = det.evaluate("CAM-01", [person], now)
    assert event is not None
    assert event.event_type == PERSON_FALLEN
    assert event.severity == "high"


def test_fall_detector_no_signal_flat_from_start():
    det = FallDetector()
    now = datetime.now(timezone.utc)
    history = [(200.0, 150.0, 0.8)]
    person = _make_tracked(
        "P#3", "person", x1=150, y1=200, x2=250, y2=215,
        stationary=0, age=6.0, history=history,
    )
    event = det.evaluate(None, [person], now)
    assert event is None


def test_event_engine_cooldown():
    engine = EventEngine(cooldown_seconds=999999)
    now = datetime.now(timezone.utc)
    from app.ai.tracker import TrackedObject
    zone_events = []
    events1 = engine.process_crowd(None, 50, now)
    assert len(events1) == 1
    events2 = engine.process_crowd(None, 50, now)
    assert len(events2) == 0
    engine._last_emitted.clear()


def test_tracker_assigns_ids():
    from app.ai.detector import Detection
    tracker = Tracker("test-cam")
    ts = datetime.now(timezone.utc)
    dets = [
        Detection(class_name="person", confidence=0.95, x1=10, y1=10, x2=50, y2=100),
        Detection(class_name="car", confidence=0.88, x1=100, y1=200, x2=300, y2=350),
    ]
    tracked = tracker.update(dets, ts)
    assert len(tracked) == 2
    ids = {t.track_id for t in tracked}
    assert "PERSON #001" in ids
    assert "VEHICLE #001" in ids