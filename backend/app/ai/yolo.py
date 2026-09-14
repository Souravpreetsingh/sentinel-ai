"""Ultralytics YOLO detector implementation.

If the model file is unavailable the detector refuses to start with a clear
error instead of silently degrading. Models are never downloaded automatically
at server startup - the operator is expected to provision the weights file.

Device selection is automatic: CUDA when available, otherwise CPU. The active
device is exposed through :meth:`YoloObjectDetector.status` and surfaced in
system health.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

from app.ai.detector import Detection, ObjectDetector, ObjectClassGovernedError, RawDetection
from app.ai.mock import (  # noqa: F401  (re-export for convenience)
    MockObjectDetector as MockObjectDetector,
)
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("ai.yolo")

_HAS_ULTRALYTICS = importlib.util.find_spec("ultralytics") is not None


def resolve_model_path(model_ref: str) -> Path | None:
    """Resolve a model reference to an on-disk file.

    Returns None if the file cannot be located. Never triggers a download.
    """
    candidates = [
        Path(model_ref),
        Path.cwd() / model_ref,
        get_settings().root_dir / model_ref,
        get_settings().root_dir / "weights" / model_ref,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _load_ultralytics():
    if not _HAS_ULTRALYTICS:
        raise ObjectClassGovernedError(
            "Ultralytics is not installed. Install AI dependencies with "
            "`pip install -r requirements-ai.txt` before using the YOLO detector."
        )
    try:
        from ultralytics import YOLO  # type: ignore

        return YOLO
    except Exception as exc:  # pragma: no cover - import failure path
        raise ObjectClassGovernedError(f"Failed to import ultralytics: {exc}") from exc


def select_device(requested: str = "") -> str:
    """Return a usable torch device string.

    Empty request -> CUDA if available, otherwise CPU. We never hard-code GPU
    availability; torch decides at runtime.
    """
    if requested:
        return requested.strip()
    try:
        import torch  # type: ignore

        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


class YoloObjectDetector(ObjectDetector):
    """YOLO (Ultralytics) based detector producing normalised detections."""

    backend_name = "yolo"

    def __init__(
        self,
        model_path: str | None = None,
        conf_threshold: float | None = None,
        device: str = "",
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        model_ref = model_path or self.settings.yolo_model
        self._conf = conf_threshold if conf_threshold is not None else self.settings.yolo_confidence
        self._device = device or self.settings.yolo_device

        resolved = resolve_model_path(model_ref)
        if resolved is None:
            raise ObjectClassGovernedError(
                f"YOLO model file '{model_ref}' is unavailable. "
                "Provision the weights file locally (for development you can download "
                "`yolo11n.pt` once) or set YOLO_MODEL/DETECTOR_BACKEND in .env. "
                "The server will not download models automatically."
            )

        self._YOLO = _load_ultralytics()
        self.model_path = resolved
        self.model_name = resolved.name
        self.device = select_device(self._device)
        self.model = self._YOLO(str(resolved))
        # Move model to the selected device while keeping default predictor args.
        if self.device:
            try:
                self.model.to(self.device)
            except Exception:  # pragma: no cover - device edge cases
                logger.warning("Could not move YOLO model to device '%s'", self.device, exc_info=True)

        # --- performance sampling ---
        self._inference_times: list[float] = []
        self._total_inferences = 0
        self._loaded = True

    def load(self) -> None:
        if not self._loaded:
            self.model = self._YOLO(str(self.model_path))
            self._loaded = True
        logger.info("YOLO model ready on %s (%s)", self.device, self.model_path)

    def _sample_inference(self, seconds: float) -> None:
        self._inference_times.append(seconds)
        if len(self._inference_times) > 500:
            self._inference_times.pop(0)

    @property
    def average_inference_ms(self) -> float:
        if not self._inference_times:
            return 0.0
        return round(1000.0 * sum(self._inference_times) / len(self._inference_times), 2)

    def status(self) -> dict[str, Any]:
        base = super().status()
        base["device"] = self.device
        base["model_path"] = str(self.model_path)
        base["confidence"] = self._conf
        base["average_inference_ms"] = self.average_inference_ms
        base["inferences_run"] = self._total_inferences
        return base

    def detect(self, frame: Any) -> list[Detection]:
        if self.model is None:
            raise ObjectClassGovernedError("YOLO model is not initialised.")

        import numpy as np

        if isinstance(frame, np.ndarray) and frame.size == 0:
            return []

        kwargs: dict[str, Any] = {"conf": self._conf, "verbose": False, "device": self.device}

        t0 = time.monotonic()
        try:
            results = self.model.predict(frame, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"YOLO inference failed: {exc}") from exc
        self._sample_inference(time.monotonic() - t0)
        self._total_inferences += 1

        detections: list[Detection] = []
        for result in results:
            boxes = getattr(getattr(result, "boxes", None), "xyxy", None)
            if boxes is None:
                continue
            boxes = boxes.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy().astype(int)
            ids = getattr(result.boxes, "id", None)
            track_ids = ids.cpu().numpy() if ids is not None else None
            names = result.names
            for idx, (box, conf, cls_id) in enumerate(zip(boxes, confs, cls_ids)):
                track_id = None
                if track_ids is not None and idx < len(track_ids):
                    track_id = str(int(track_ids[idx]))
                raw = RawDetection(
                    class_name=str(names.get(int(cls_id), "unknown")),
                    confidence=float(conf),
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                    track_id=track_id,
                )
                detection = ObjectDetector.build_detection(raw)
                if detection is not None:
                    detections.append(detection)
        return detections


def dependency_status() -> str:
    """Human readable check used by /api/system/health and CLI --check."""
    if not _HAS_ULTRALYTICS:
        return "unavailable (ultralytics not installed)"
    resolved = resolve_model_path(get_settings().yolo_model)
    if resolved is None:
        return f"unavailable (model '{get_settings().yolo_model}' not found)"
    return f"available ({resolved})"


def main() -> None:  # pragma: no cover - CLI helper
    status = dependency_status()
    print(f"SENTINEL AI - YOLO dependency check")
    print(f"  ultralytics installed : {_HAS_ULTRALYTICS}")
    hint = ""
    if not _HAS_ULTRALYTICS:
        hint = "  -> pip install -r requirements-ai.txt\n"
    elif dependency_status().startswith("unavailable"):
        hint = f"  -> provision weights at: {get_settings().root_dir / get_settings().yolo_model}\n"
    print(f"  model '{get_settings().yolo_model}': {status}")
    print(hint, end="")
    if status.startswith("unavailable"):
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    sys.exit(main())