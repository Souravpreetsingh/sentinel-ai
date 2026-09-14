"""Zone detection tests."""

from datetime import datetime, timezone

from app.ai.tracker import TrackedObject
from app.ai.zones import Zone, ZoneAnalyzer, ZoneConfig


def _point_in_square_zone():
    return Zone(
        name="Restricted Zone B",
        points=[(200, 200), (400, 200), (400, 400), (200, 400)],
    )


def test_zone_contains_point_inside():
    zone = _point_in_square_zone()
    assert zone.contains(300, 300) is True
    assert zone.contains(200, 200) is True
    assert zone.contains(199, 199) is False


def test_zone_contains_center_bbox_inside():
    zone = _point_in_square_zone()
    assert zone.contains_bbox(250, 250, 350, 350) is True
    assert zone.contains_bbox(50, 50, 100, 100) is False


def test_zone_entry_detected():
    zone = _point_in_square_zone()
    analyzer = ZoneAnalyzer(zones=[zone])
    now = datetime.now(timezone.utc)
    person_inside = TrackedObject(
        track_id="PERSON #001",
        class_name="person",
        category="person",
        confidence=0.9,
        x1=250, y1=250, x2=300, y2=350,
        first_seen=now, last_seen=now, last_moved_at=now,
        history=[((275, 300, 1.5))],
    )
    events = analyzer.update("CAM-07", [person_inside], now)
    assert len(events) == 1
    assert events[0].zone_name == "Restricted Zone B"
    assert events[0].event_type == "restricted_zone_entry"
    assert "PERSON #001" in events[0].inside_track_ids
    # Second update should not emit (no new entry).
    events2 = analyzer.update("CAM-07", [person_inside], now)
    assert len(events2) == 0


def test_zone_exit_removes_membership():
    zone = _point_in_square_zone()
    analyzer = ZoneAnalyzer(zones=[zone])
    now = datetime.now(timezone.utc)
    person = TrackedObject(
        track_id="P#01", class_name="person", category="person",
        confidence=0.9, x1=300, y1=300, x2=350, y2=380,
        first_seen=now, last_seen=now, last_moved_at=now,
        history=[(325, 340, 1.0)],
    )
    analyzer.update("CAM-07", [person], now)
    # Now move outside.
    person_outside = TrackedObject(
        track_id="P#01", class_name="person", category="person",
        confidence=0.9, x1=10, y1=10, x2=50, y2=80,
        first_seen=now, last_seen=now, last_moved_at=now,
        history=[(30, 45, 1.0)],
    )
    events = analyzer.update("CAM-07", [person_outside], now)
    assert len(events) == 0


def test_zone_config_to_zone():
    cfg = ZoneConfig(name="Zone A", points=[(0, 0), (100, 0), (100, 100), (0, 100)])
    zone = cfg.to_zone()
    assert zone.name == "Zone A"
    assert zone.contains(50, 50) is True