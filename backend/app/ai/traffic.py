"""Rule-based traffic congestion heuristic.

Drives an approximate vehicle density ratio per camera from currently tracked
vehicles. When the ratio exceeds a configurable threshold a
``traffic_congestion`` event is emitted.

This is deliberately labelled as *AI-estimated traffic activity*, not an exact
traffic engineering measurement.
"""

from __future__ import annotations

from datetime import datetime

from app.ai.tracker import TrackedObject
from app.ai.types import TRAFFIC_CONGESTION, DetectionEvent


class TrafficCongestionAnalyzer:
    """Flags sustained high vehicle density on a given camera."""

    def __init__(
        self,
        threshold: float = 0.75,
        capacity: int = 6,
        min_vehicles: int = 3,
    ) -> None:
        self.threshold = max(0.0, min(1.0, threshold))
        self.capacity = max(1, capacity)
        self.min_vehicles = max(1, min_vehicles)

    def reset(self) -> None:
        pass

    def density(self, tracked: list[TrackedObject]) -> float:
        vehicles = sum(1 for o in tracked if o.category == "vehicle")
        return min(1.0, vehicles / self.capacity)

    def evaluate(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> DetectionEvent | None:
        vehicles = [o for o in tracked if o.category == "vehicle"]
        if len(vehicles) < self.min_vehicles:
            return None
        density = min(1.0, len(vehicles) / self.capacity)
        if density < self.threshold:
            return None
        return DetectionEvent(
            event_id="",
            event_type=TRAFFIC_CONGESTION,
            severity="medium",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=round(min(0.9, 0.5 + density * 0.4), 3),
            objects=[
                {
                    "class_name": o.class_name,
                    "track_id": o.track_id,
                    "bbox": [round(o.x1, 1), round(o.y1, 1), round(o.x2, 1), round(o.y2, 1)],
                }
                for o in vehicles
            ],
            metadata={
                "density": round(density, 3),
                "vehicles_count": len(vehicles),
                "note": "AI-estimated traffic activity, not an exact traffic engineering measurement.",
            },
        )