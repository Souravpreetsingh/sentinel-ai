"""Detector factory.

- ``auto``: try YOLO (installed + model present), otherwise fall back to the
  mock detector with a clear log message.
- ``yolo``: real YOLO detector; raises a clear error if it cannot initialise.
- ``mock``: deterministic development detector.
"""

from __future__ import annotations

from app.ai.detector import ObjectDetector, ObjectClassGovernedError
from app.ai.mock import MockObjectDetector
from app.ai.yolo import YoloObjectDetector, dependency_status, resolve_model_path
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("ai.factory")


def build_detector(settings: Settings | None = None) -> ObjectDetector:
    settings = settings or get_settings()
    backend = settings.detector_backend.strip().lower()

    if backend == "mock":
        logger.info("Detector backend: mock")
        return MockObjectDetector()

    if backend == "yolo":
        if not dependency_status().startswith("available"):
            raise ObjectClassGovernedError(
                f"Cannot initialise YOLO detector (DETECTOR_BACKEND=yolo). {dependency_status()}"
            )
        logger.info("Detector backend: yolo (%s)", settings.yolo_model)
        return YoloObjectDetector()

    if backend == "auto":
        from app.ai.yolo import _HAS_ULTRALYTICS

        if _HAS_ULTRALYTICS and resolve_model_path(settings.yolo_model) is not None:
            logger.info("Detector backend: yolo (auto) using %s", settings.yolo_model)
            return YoloObjectDetector()
        logger.warning(
            "Detector backend: mock (auto). YOLO %s. "
            "Set DETECTOR_BACKEND=yolo after installing AI deps to use real inference.",
            dependency_status(),
        )
        return MockObjectDetector()

    raise ValueError(
        f"Unknown DETECTOR_BACKEND '{settings.detector_backend}'. "
        "Expected one of: auto, yolo, mock."
    )