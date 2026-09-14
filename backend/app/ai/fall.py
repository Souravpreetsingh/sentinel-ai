"""Basic person-fall event abstraction.

A purely geometric heuristic: a person track that quickly transitions from a
tall bounding box (upright) to a wide/short one (lying/flat) while moving
downward fast is flagged as a *possible* fall.

This is not a medical determination. Events are emitted with high severity and
a confidence that deliberately reflects uncertainty.
"""

from __future__ import annotations

from datetime import datetime

from app.ai.types import PERSON_FALLEN, DetectionEvent
from app.ai.tracker import TrackedObject

# Upright person: height > 1.4 * width. Lying person: height <= 0.9 * width.
_TALL_ASPECT = 1.4
_FLAT_ASPECT = 0.9


class FallDetector:
    def __init__(self, velocity_threshold: float = 6.0) -> None:
        self.velocity_threshold = max(0.1, velocity_threshold)
        self._reported: set[str] = set()

    def reset(self) -> None:
        self._reported.clear()

    def evaluate(
        self, camera_id: str | None, tracked: list[TrackedObject], timestamp: datetime
    ) -> DetectionEvent | None:
        for obj in tracked:
            if obj.class_name != "person" or obj.track_id in self._reported:
                continue
            signal = self._fall_signal(obj)
            if signal is None:
                continue
            self._reported.add(obj.track_id)
            return DetectionEvent(
                event_id="",
                event_type=PERSON_FALLEN,
                severity="high",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=round(signal[0], 3),
                objects=[
                    {
                        "class_name": obj.class_name,
                        "track_id": obj.track_id,
                        "bbox": [round(obj.x1, 1), round(obj.y1, 1), round(obj.x2, 1), round(obj.y2, 1)],
                    }
                ],
                metadata={
                    "aspect_now": round(signal[1], 2),
                    "aspect_before": round(signal[2], 2),
                    "vertical_speed": round(signal[3], 2),
                    "disclaimer": "Possible person fall - heuristic only, not a medical determination.",
                },
            )
        return None

    def _fall_signal(self, obj: TrackedObject) -> tuple[float, float, float, float] | None:
        """Return (confidence, aspect_now, aspect_before, vertical_speed) or None."""
        aspect_now = obj.aspect_ratio
        if aspect_now > _FLAT_ASPECT:
            return None
        if obj.age_seconds < 3.0 or obj.frame_count < 6:
            return None

        aspect_before = 0.0
        for entry in obj.history[:-1]:
            if len(entry) >= 3:
                past_aspect = entry[2]
                if past_aspect > _TALL_ASPECT:
                    aspect_before = past_aspect
                    break

        # Downward vertical speed measured on the bbox bottom.
        vspeed = 0.0
        if len(obj.history) >= 2:
            prev = obj.history[-2]
            vspeed = obj.center[1] - prev[1]

        if aspect_before <= 0.0:
            return None

        confidence = min(0.9, 0.5 + 0.08 * (abs(vspeed) / self.velocity_threshold))
        return confidence, aspect_now, aspect_before, vspeed