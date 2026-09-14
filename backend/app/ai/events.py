"""Rule-based event engine.

Combines the individual analyzers (zones, crowd, abandoned object, stopped
vehicle, person fall) into a single stream of :class:`DetectionEvent` and
applies per-(camera, type) cooldowns to avoid spamming duplicates.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from app.ai.abandoned import AbandonedObjectDetector
from app.ai.crowd import CrowdAnalyzer
from app.ai.fall import FallDetector
from app.ai.traffic import TrafficCongestionAnalyzer
from app.ai.tracker import TrackedObject
from app.ai.types import (
    ABANDONED_OBJECT,
    ACCIDENT,
    CROWD_DENSITY_HIGH,
    DetectionEvent,
    EVENT_SEVERITIES,
    PERSON_FALLEN,
    POSSIBLE_PERSON_FALL,
    RESTRICTED_ZONE_ENTRY,
    TRAFFIC_CONGESTION,
    VEHICLE_STOPPED,
)
from app.ai.vehicle_stopped import VehicleStoppedDetector
from app.ai.zones import Zone, ZoneAnalyzer, ZoneEvent
from app.core.logging import get_logger

logger = get_logger("ai.events")


def objects_payload(tracked: list[TrackedObject], limit: int = 25) -> list[dict]:
    return [
        {
            "class_name": o.class_name,
            "track_id": o.track_id,
            "confidence": round(o.confidence, 3),
            "bbox": [round(o.x1, 1), round(o.y1, 1), round(o.x2, 1), round(o.y2, 1)],
        }
        for o in tracked[:limit]
    ]


class EventEngine:
    """Consolidates rule outputs into cooldown-limited events."""

    def __init__(
        self,
        crowd: CrowdAnalyzer | None = None,
        abandoned: AbandonedObjectDetector | None = None,
        stopped: VehicleStoppedDetector | None = None,
        fall: FallDetector | None = None,
        traffic: TrafficCongestionAnalyzer | None = None,
        zones: ZoneAnalyzer | None = None,
        cooldown_seconds: float = 10.0,
    ) -> None:
        self.crowd = crowd or CrowdAnalyzer()
        self.abandoned = abandoned or AbandonedObjectDetector()
        self.stopped = stopped or VehicleStoppedDetector()
        self.fall = fall or FallDetector()
        self.traffic = traffic or TrafficCongestionAnalyzer()
        self.zones = zones or ZoneAnalyzer()
        self.cooldown_seconds = cooldown_seconds
        self._last_emitted: dict[tuple[str, str], float] = {}

    # -- zone configuration handled by the caller -------------------------
    @property
    def zone_analyzer(self) -> ZoneAnalyzer:
        return self.zones

    def set_zones(self, zones: list[Zone]) -> None:
        self.zones.set_zones(zones)

    def _cooldown_ok(self, camera_id: str | None, event_type: str, now: float) -> bool:
        key = (camera_id or "default", event_type)
        last = self._last_emitted.get(key)
        if last is not None and now - last < max(0.0, self.cooldown_seconds):
            return False
        self._last_emitted[key] = now
        return True

    def _make(
        self,
        event_type: str,
        camera_id: str | None,
        timestamp: datetime,
        confidence: float,
        objects: list[dict],
        metadata: dict | None = None,
    ) -> DetectionEvent | None:
        if not self._cooldown_ok(camera_id, event_type, time.time()):
            return None
        return DetectionEvent(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            severity=EVENT_SEVERITIES.get(event_type, "medium"),
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=confidence,
            objects=objects,
            metadata=metadata or {},
        )

    def process_zone_events(
        self, camera_id: str | None, zone_events: list[ZoneEvent]
    ) -> list[DetectionEvent]:
        out: list[DetectionEvent] = []
        for ze in zone_events:
            event = self._make(
                event_type=ze.event_type,
                camera_id=camera_id,
                timestamp=ze.timestamp,
                confidence=0.9,
                objects=[
                    {"class_name": c, "track_id": tid}
                    for c, tid in zip(ze.object_classes, ze.inside_track_ids)
                ],
                metadata={"zone": ze.zone_name, "track_ids": ze.inside_track_ids},
            )
            if event is not None:
                out.append(event)
        return out

    def process_crowd(
        self, camera_id: str | None, people_count: int, timestamp: datetime
    ) -> list[DetectionEvent]:
        event = self.crowd.evaluate(camera_id, people_count, timestamp)
        if event is None:
            return []
        if not self._cooldown_ok(camera_id, event.event_type, time.time()):
            return []
        return [event]

    def process_abandoned(
        self,
        camera_id: str | None,
        tracked: list[TrackedObject],
        timestamp: datetime,
    ) -> list[DetectionEvent]:
        event = self.abandoned.evaluate(camera_id, tracked, timestamp)
        if event is None:
            return []
        if not self._cooldown_ok(camera_id, event.event_type, time.time()):
            return []
        return [event]

    def process_stopped(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> list[DetectionEvent]:
        event = self.stopped.evaluate(camera_id, tracked, timestamp)
        if event is None:
            return []
        if not self._cooldown_ok(camera_id, event.event_type, time.time()):
            return []
        return [event]

    def process_fall(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> list[DetectionEvent]:
        event = self.fall.evaluate(camera_id, tracked, timestamp)
        if event is None:
            return []
        if not self._cooldown_ok(camera_id, event.event_type, time.time()):
            return []
        return [event]

    def process_traffic(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> list[DetectionEvent]:
        event = self.traffic.evaluate(camera_id, tracked, timestamp)
        if event is None:
            return []
        if not self._cooldown_ok(camera_id, event.event_type, time.time()):
            return []
        return [event]

    def run(
        self,
        camera_id: str | None,
        tracked: list[TrackedObject],
        timestamp: datetime,
        zone_events: list[ZoneEvent] | None = None,
        people_count: int | None = None,
    ) -> list[DetectionEvent]:
        """Run the full rule pipeline for one frame."""
        timestamp = timestamp or datetime.now(timezone.utc)
        zone_events = zone_events or self.zones.update(camera_id, tracked, timestamp)

        events: list[DetectionEvent] = []
        events.extend(self.process_zone_events(camera_id, zone_events))

        if people_count is None:
            people_count = sum(1 for o in tracked if o.category == "person")
        events.extend(self.process_crowd(camera_id, people_count, timestamp))
        events.extend(self.process_abandoned(camera_id, tracked, timestamp))
        events.extend(self.process_stopped(camera_id, tracked, timestamp))
        events.extend(self.process_fall(camera_id, tracked, timestamp))
        events.extend(self.process_traffic(camera_id, tracked, timestamp))
        return events