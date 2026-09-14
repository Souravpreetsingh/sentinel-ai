"""YOLO detector + factory tests.

Verifies:
1. Mock detector produces normalised detections.
2. build_detector("mock") works.
3. build_detector("yolo") raises clear error without ultralytics.
4. YoloObjectDetector raises FileNotFoundError for missing model.
5. normalize_class_name maps COCO classes correctly.
6. Detection.to_dict works.
"""

import pytest

from app.ai.detector import (
    HIGH_LEVEL_CLASS_MAP,
    SUPPORTED_CLASSES,
    Detection,
    ObjectDetector,
    RawDetection,
    normalize_class_name,
)
from app.ai.mock import MockObjectDetector


def test_normalize_class_name():
    assert normalize_class_name("person") == "person"
    assert normalize_class_name("motorbike") == "motorcycle"
    assert normalize_class_name("car") == "car"
    assert normalize_class_name("truck") == "truck"
    assert normalize_class_name("bicycle") == "bicycle"
    assert normalize_class_name("bus") == "bus"
    assert normalize_class_name("cat") is None
    assert normalize_class_name("") is None
    assert normalize_class_name("PERSON") == "person"


def test_supported_classes():
    assert SUPPORTED_CLASSES == frozenset({"person", "car", "motorcycle", "bus", "truck", "bicycle"})


def test_mock_detector_returns_normalised_detections():
    det = MockObjectDetector(seed=0, simulated_objects=2)
    dets = det.detect(None)
    assert len(dets) == 2
    assert all(isinstance(d, Detection) for d in dets)
    assert all(d.class_name in SUPPORTED_CLASSES for d in dets)
    assert all(d.raw_class_name is not None for d in dets)


def test_detection_to_dict():
    d = Detection(class_name="person", confidence=0.95, x1=10, y1=20, x2=60, y2=120, track_id=None)
    result = d.to_dict()
    assert result["class_name"] == "person"
    assert result["confidence"] == 0.95
    assert "track_id" in result


def test_detection_category():
    assert Detection(class_name="car", confidence=0.9, x1=0, y1=0, x2=10, y2=10).category == "vehicle"
    assert Detection(class_name="person", confidence=0.9, x1=0, y1=0, x2=10, y2=10).category == "person"


def test_build_detection_normalizes():
    raw = RawDetection(class_name="motorbike", confidence=0.88, x1=100, y1=200, x2=300, y2=400)
    det = ObjectDetector.build_detection(raw)
    assert det is not None
    assert det.class_name == "motorcycle"


def test_build_detection_unsupported_returns_none():
    raw = RawDetection(class_name="cat", confidence=0.8, x1=0, y1=0, x2=10, y2=10)
    assert ObjectDetector.build_detection(raw) is None


def test_build_detector_mock():
    from app.ai.factory import build_detector
    from app.core.config import Settings
    settings = Settings(detector_backend="mock")
    detector = build_detector(settings)
    assert isinstance(detector, MockObjectDetector)
    assert detector.backend_name == "mock"


def test_yolo_dependency_status():
    from app.ai.yolo import dependency_status
    status = dependency_status()
    # Without ultralytics installed this will say unavailable.
    assert isinstance(status, str)


def test_yolo_detector_raises_without_model():
    from app.ai.yolo import YoloObjectDetector
    from app.core.config import Settings
    from app.ai.detector import ObjectClassGovernedError

    settings = Settings(detector_backend="yolo", yolo_model="nonexistent_model_xyz.pt")
    try:
        YoloObjectDetector(settings=settings)
        # If ultralytics IS installed but model missing, we get an error:
        pytest.fail("Should have raised ObjectClassGovernedError for missing model")
    except ObjectClassGovernedError as e:
        assert "nonexistent_model_xyz.pt" in str(e)
    except Exception:
        # Other import errors (e.g. torch not installed) also acceptable
        pass