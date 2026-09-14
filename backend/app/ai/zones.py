"""Polygonal virtual zone analysis.

Zones are used to detect *movement / presence* of people (or vehicles) only.
We deliberately do not identify or attribute identity to any person.

A zone is represented as: ``id, name, type, polygon, enabled`` where type is
one of ``restricted`` / ``monitoring`` / ``traffic``.
"""

from __future__ import annotations

import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.ai.tracker import TrackedObject

DEFAULT_ZONE_EVENT_TYPE = "restricted_zone_entry"
DEFAULT_ZONE_SEVERITY = "high"

RESTRICTED = "restricted"
MONITORING = "monitoring"
TRAFFIC = "traffic"

# Zones of a given type monitor these object classes by default.
ZONE_MONITORED_CLASSES: dict[str, tuple[str, ...]] = {
    RESTRICTED: ("person",),
    MONITORING: ("person",),
    TRAFFIC: ("vehicle",),
}


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(slots=True)
class Zone:
    """A named polygonal region on the video frame."""

    name: str
    points: tuple[Point, ...]
    zone_type: str = RESTRICTED   # restricted | monitoring | traffic
    enabled: bool = True
    id: str = ""
    event_type: str | None = None  # override; otherwise derived from zone_type
    severity: str = DEFAULT_ZONE_SEVERITY

    def __post_init__(self) -> None:
        coerced: list[Point] = []
        for pt in self.points:
            if isinstance(pt, Point):
                coerced.append(pt)
            else:
                try:
                    x, y = pt
                except (TypeError, ValueError):
                    continue
                coerced.append(Point(float(x), float(y)))
        self.points = tuple(coerced)
        if not self.id:
            slug = re.sub(r"[^a-z0-9]+", "-", self.name.strip().lower()).strip("-")
            self.id = slug or uuid.uuid4().hex
        if not self.event_type:
            default = {
                RESTRICTED: "restricted_zone_entry",
                MONITORING: "zone_presence",
                TRAFFIC: "zone_vehicle_entry",
            }
            self.event_type = default.get(self.zone_type, DEFAULT_ZONE_EVENT_TYPE)

    # -- spec aliases -----------------------------------------------------
    @property
    def polygon(self) -> tuple[Point, ...]:
        return self.points

    @property
    def type(self) -> str:
        return self.zone_type

    # -- geometry ---------------------------------------------------------
    def contains(self, x: float, y: float) -> bool:
        inside = False
        n = len(self.points)
        if n < 3:
            return False
        j = n - 1
        for i in range(n):
            xi, yi = self.points[i].x, self.points[i].y
            xj, yj = self.points[j].x, self.points[j].y
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside

    def bbox_center(self, x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def contains_bbox(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        cx, cy = self.bbox_center(x1, y1, x2, y2)
        return self.contains(cx, cy)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.zone_type,
            "enabled": self.enabled,
            "polygon": [[p.x, p.y] for p in self.points],
            "event_type": self.event_type,
            "severity": self.severity,
        }


@dataclass(slots=True)
class ZoneEvent:
    event_type: str
    severity: str
    zone_name: str
    camera_id: str | None
    timestamp: datetime
    inside_track_ids: list[str]
    object_classes: list[str]

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "zone": self.zone_name,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "track_ids": self.inside_track_ids,
            "object_classes": self.object_classes,
        }


@dataclass(slots=True)
class ZoneConfig:
    """Simple JSON-able zone definition for configuration."""

    name: str
    points: list[tuple[float, float]]
    zone_type: str = RESTRICTED
    enabled: bool = True
    id: str = ""
    event_type: str | None = None
    severity: str = DEFAULT_ZONE_SEVERITY

    def to_zone(self) -> Zone:
        return Zone(
            name=self.name,
            points=tuple(Point(x, y) for x, y in self.points),
            zone_type=self.zone_type,
            enabled=self.enabled,
            id=self.id,
            event_type=self.event_type,
            severity=self.severity,
        )


class ZoneAnalyzer:
    """Stateful per-camera zone entry detection.

    Only emits an event the *first* time a given track enters a zone, and only
    for object classes relevant to the zone type (people for restricted /
    monitoring, vehicles for traffic zones).
    """

    def __init__(self, zones: list[Zone] | None = None) -> None:
        self.zones = zones or []
        self._inside: dict[str, set[str]] = {}

    def set_zones(self, zones: list[Zone]) -> None:
        self.zones = zones
        self._inside.clear()

    def _zones_for(self, camera_id: str) -> str:
        return camera_id or "default"

    def enabled_zones(self) -> list[Zone]:
        return [z for z in self.zones if z.enabled]

    def update(
        self,
        camera_id: str | None,
        tracked: list[TrackedObject],
        timestamp: datetime | None = None,
    ) -> list[ZoneEvent]:
        """Return zone-entry events for newly entered objects."""
        now = timestamp or datetime.now(timezone.utc)
        key = self._zones_for(camera_id)
        inside = self._inside.setdefault(key, set())
        events: list[ZoneEvent] = []

        for zone in self.enabled_zones():
            monitored = ZONE_MONITORED_CLASSES.get(zone.zone_type, ("person",))
            current: set[str] = set()
            classes: set[str] = set()
            for obj in tracked:
                if obj.class_name not in monitored:
                    continue
                cx, cy = obj.center
                if zone.contains(cx, cy):
                    current.add(obj.track_id)
                    classes.add(obj.class_name)

            newly = current - inside
            if newly:
                events.append(
                    ZoneEvent(
                        event_type=zone.event_type,
                        severity=zone.severity,
                        zone_name=zone.name,
                        camera_id=camera_id,
                        timestamp=now,
                        inside_track_ids=sorted(current),
                        object_classes=sorted(classes),
                    )
                )
            inside.update(newly)

        # Drop stale zone membership for objects that are no longer tracked.
        alive = {o.track_id for o in tracked}
        inside.intersection_update(alive)
        return events