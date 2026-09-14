"""Vehicle-stopped detection based on tracking data.

A vehicle that stays approximately stationary for a configurable duration is
flagged as ``vehicle_stopped`` (potential breakdown / accident / congestion).
"""

from __future__ import annotations

from datetime import datetime

from app.ai.types import VEHICLE_STOPPED, DetectionEvent
from app.ai.tracker import TrackedObject


class VehicleStoppedDetector:
    def __init__(self, stationary_seconds: float = 20.0) -> None:
        self.stationary_seconds = stationary_seconds
        self._reported: set[str] = set()

    def reset(self) -> None:
        self._reported.clear()

    def evaluate(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> DetectionEvent | None:
        stopped: list[TrackedObject] = []
        for obj in tracked:
            if obj.category != "vehicle":
                continue
            if obj.stationary_seconds >= self.stationary_seconds:
                stopped.append(obj)

        if not stopped:
            return None

        unreported = [s for s in stopped if s.track_id not in self._reported]
        if not unreported:
            return None

        target = max(unreported, key=lambda s: s.stationary_seconds)
        self._reported.add(target.track_id)

        return DetectionEvent(
            event_id="",
            event_type=VEHICLE_STOPPED,
            severity="medium",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=round(min(0.95, 0.6 + target.stationary_seconds / 600.0), 3),
            objects=[
                {
                    "class_name": target.class_name,
                    "track_id": target.track_id,
                    "bbox": [round(target.x1, 1), round(target.y1, 1), round(target.x2, 1), round(target.y2, 1)],
                }
            ],
            metadata={
                "stationary_seconds": round(target.stationary_seconds, 1),
                "stationary_vehicles": len(stopped),
                "threshold_seconds": self.stationary_seconds,
            },
        )