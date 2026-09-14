"""Shared event types and constants.

Kept in a leaf module (no imports from analyzers) to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# --------------------------------------------------------------------------
# Canonical / supported event types.
# --------------------------------------------------------------------------
RESTRICTED_ZONE_ENTRY = "restricted_zone_entry"
CROWD_DENSITY_HIGH = "crowd_density_high"
ABANDONED_OBJECT = "abandoned_object"
VEHICLE_STOPPED = "vehicle_stopped"
PERSON_FALLEN = "possible_person_fall"
POSSIBLE_PERSON_FALL = PERSON_FALLEN  # user-facing label for the fall rule
ACCIDENT = "accident"
TRAFFIC_CONGESTION = "traffic_congestion"

EVENT_SEVERITIES: dict[str, str] = {
    RESTRICTED_ZONE_ENTRY: "high",
    CROWD_DENSITY_HIGH: "medium",
    ABANDONED_OBJECT: "medium",
    VEHICLE_STOPPED: "medium",
    PERSON_FALLEN: "high",
    ACCIDENT: "high",
    TRAFFIC_CONGESTION: "medium",
}


@dataclass(slots=True)
class DetectionEvent:
    event_id: str
    event_type: str
    severity: str
    camera_id: str | None
    timestamp: datetime
    confidence: float
    objects: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "confidence": round(self.confidence, 3),
            "objects": self.objects,
            "metadata": self.metadata,
        }