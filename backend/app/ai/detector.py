"""Detector abstraction for the SENTINEL AI video pipeline.

The rest of the backend only depends on :class:`ObjectDetector` and
:class:`Detection`. Concrete detectors (YOLO, mock, ...) are replaceable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


class ObjectClassGovernedError(RuntimeError):
    """Raised when a detector cannot be initialised (missing model, deps)."""


# Supported internal class names (normalised from model output).
SUPPORTED_CLASSES = frozenset({"person", "car", "motorcycle", "bus", "truck", "bicycle"})

# Normalisation map: model class name (COCO style) -> internal SENTINEL name.
HIGH_LEVEL_CLASS_MAP: dict[str, str] = {
    "person": "person",
    "car": "car",
    "motorbike": "motorcycle",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "truck": "truck",
    "bicycle": "bicycle",
}

VEHICLE_CLASSES = frozenset({"car", "motorcycle", "bus", "truck", "bicycle"})


def normalize_class_name(raw: str) -> str | None:
    """Map a model class name into our internal naming scheme."""
    key = (raw or "").strip().lower()
    return HIGH_LEVEL_CLASS_MAP.get(key)


@dataclass(slots=True)
class Detection:
    """A structured, normalised detection produced by the pipeline."""

    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    track_id: Optional[str] = None
    raw_class_name: Optional[str] = None

    @property
    def category(self) -> str:
        if self.class_name == "person":
            return "person"
        if self.class_name in VEHICLE_CLASSES:
            return "vehicle"
        return "other"

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return max(0.0, (self.x2 - self.x1) * (self.y2 - self.y1))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RawDetection:
    """Output of a concrete model before normalisation."""

    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    track_id: Optional[str] = None


class ObjectDetector(ABC):
    """Abstract detector. Concrete implementations load their own model."""

    backend_name: str = "abstract"
    model_name: str = "abstract"
    supported_classes: frozenset[str] = SUPPORTED_CLASSES

    @abstractmethod
    def detect(self, frame: Any) -> list[Detection]:
        """Run inference on a single frame, return normalised detections."""

    def load(self) -> None:
        """Explicitly load the model (idempotent). Concrete detectors may no-op."""

    def status(self) -> dict[str, Any]:
        return {
            "backend": self.backend_name,
            "model": self.model_name,
            "loaded": True,
            "supported_classes": sorted(self.supported_classes),
        }

    @classmethod
    def build_detection(cls, raw: RawDetection) -> Detection | None:
        """Normalise a raw model detection into an internal Detection."""
        normalised = normalize_class_name(raw.class_name)
        if normalised is None:
            return None
        return Detection(
            class_name=normalised,
            confidence=float(raw.confidence),
            x1=float(raw.x1),
            y1=float(raw.y1),
            x2=float(raw.x2),
            y2=float(raw.y2),
            track_id=raw.track_id,
            raw_class_name=str(raw.class_name),
        )