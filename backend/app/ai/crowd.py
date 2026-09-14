"""Crowd density estimation.

Simple occupancy-based rules with configurable thresholds:

- LOW:    0-15 people
- MEDIUM: 16-30 people
- HIGH:   31+ people
"""

from __future__ import annotations

from app.ai.types import CROWD_DENSITY_HIGH, DetectionEvent


class CrowdAnalyzer:
    def __init__(self, low_max: int = 15, medium_max: int = 30) -> None:
        self.low_max = low_max
        self.medium_max = medium_max

    def classify(self, count: int) -> str:
        if count <= self.low_max:
            return "LOW"
        if count <= self.medium_max:
            return "MEDIUM"
        return "HIGH"

    def evaluate(self, camera_id: str | None, people_count: int, timestamp) -> DetectionEvent | None:
        level = self.classify(people_count)
        if level == "LOW":
            return None
        confidence = min(0.99, 0.6 + people_count / 200.0)
        return DetectionEvent(
            event_id="",
            event_type=CROWD_DENSITY_HIGH,
            severity="high" if level == "HIGH" else "medium",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=round(confidence, 3),
            objects=[],
            metadata={
                "crowd_level": level,
                "people_count": people_count,
                "thresholds": {"low": self.low_max, "medium": self.medium_max},
                "note": "Occupancy estimate - density rule, not an identity scan.",
            },
        )

    def thresholds(self) -> dict:
        return {"low_max": self.low_max, "medium_max": self.medium_max}