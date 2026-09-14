"""Deterministic mock detector for development, demos and tests.

Produces the same detections for the same inputs so tests are stable. It emits
normalised internal class names already (person / car / bicycle / ...).
"""

from __future__ import annotations

import random
from typing import Any

from app.ai.detector import Detection, ObjectDetector


class MockObjectDetector(ObjectDetector):
    backend_name = "mock"
    model_name = "mock-object-detector"

    def __init__(self, seed: int = 42, simulated_objects: int = 3) -> None:
        self.seed = seed
        self.simulated_objects = max(1, simulated_objects)
        self._rng = random.Random(seed)
        self._motion_phase = [self._rng.random() * 6.28 for _ in range(self.simulated_objects)]

    def status(self) -> dict[str, Any]:
        base = super().status()
        base["note"] = "Development mock detector - not real inference."
        return base

    def detect(self, frame: Any) -> list[Detection]:
        width, height = 640, 480
        if frame is not None:
            try:
                candidate_height, candidate_width = frame.shape[:2]
                if candidate_width > 0 and candidate_height > 0:
                    width, height = candidate_width, candidate_height
            except (AttributeError, ValueError):
                pass

        classes = ["person", "car", "bicycle"]
        detections: list[Detection] = []
        frame_index = getattr(frame, "_sentinel_frame_index", None)

        for i in range(self.simulated_objects):
            self._motion_phase[i] += 0.12
            phase = self._motion_phase[i]
            cx = width * (0.25 + 0.5 * (0.5 + 0.5 * __import__("math").sin(phase)))
            cy = height * (0.35 + 0.2 * __import__("math").sin(phase * 0.7))
            w = width * (0.04 + 0.03 * (i % 2))
            h = height * (0.09 + 0.04 * (i % 2))
            confidence = round(0.72 + (0.20 * ((i * 7919 + 13) % 100) / 100), 2)

            detections.append(
                Detection(
                    class_name=classes[i % len(classes)],
                    confidence=confidence,
                    x1=round(cx - w / 2, 2),
                    y1=round(cy - h, 2),
                    x2=round(cx + w / 2, 2),
                    y2=round(cy, 2),
                    track_id=None,
                    raw_class_name=classes[i % len(classes)],
                )
            )
            if frame_index is not None:
                detections[-1].to_dict.__getattribute__  # no-op for symmetry

        return detections