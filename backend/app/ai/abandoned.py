"""Rule-based abandoned object detection.

This is a deliberately simple heuristic: objects matching a configured class
set that remain stationary for a configurable duration with no person nearby
are flagged. It is *not* promised as perfect security detection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.ai.types import ABANDONED_OBJECT, DetectionEvent
from app.ai.tracker import TrackedObject


class AbandonedObjectDetector:
    def __init__(
        self,
        stationary_seconds: float = 30.0,
        object_classes: tuple[str, ...] = ("bag", "backpack", "suitcase", "box"),
        proximity_radius: float = 90.0,
    ) -> None:
        self.stationary_seconds = stationary_seconds
        self.object_classes = tuple(c.lower() for c in object_classes)
        self.proximity_radius = proximity_radius
        self._reported: set[str] = set()

    def reset(self) -> None:
        self._reported.clear()

    def evaluate(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> DetectionEvent | None:
        # Candidate objects: matching class, stationary long enough, and no
        # person within proximity.
        candidate: TrackedObject | None = None
        people = [o for o in tracked if o.class_name == "person"]

        for obj in tracked:
            if obj.class_name not in self.object_classes:
                continue
            if obj.stationary_seconds < self.stationary_seconds:
                continue
            near_person = any(
                _bbox_proximity(obj, p) < self.proximity_radius for p in people
            )
            if near_person:
                continue
            candidate = obj
            break

        if candidate is None:
            return None
        if candidate.track_id in self._reported:
            return None
        self._reported.add(candidate.track_id)

        return DetectionEvent(
            event_id="",
            event_type=ABANDONED_OBJECT,
            severity="medium",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=round(min(0.95, 0.6 + candidate.stationary_seconds / 300.0), 3),
            objects=[
                {
                    "class_name": candidate.class_name,
                    "track_id": candidate.track_id,
                    "bbox": [round(candidate.x1, 1), round(candidate.y1, 1), round(candidate.x2, 1), round(candidate.y2, 1)],
                }
            ],
            metadata={
                "stationary_seconds": round(candidate.stationary_seconds, 1),
                "threshold_seconds": self.stationary_seconds,
                "note": "Basic rule-based heuristic. Treat as an alert to review, not a confirmed security finding.",
            },
        )


def _bbox_proximity(a: TrackedObject, b: TrackedObject) -> float:
    acx, acy = a.center
    bcx, bcy = b.center
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5