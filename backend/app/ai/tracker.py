"""Object tracking across frames with per-camera state.

Every tracked object receives a stable, human readable ID such as
``PERSON #024`` or ``VEHICLE #091``. Association is IoU + centroid based -
purposefully simple and replaceable.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.ai.detector import Detection, VEHICLE_CLASSES
from app.core.logging import get_logger

logger = get_logger("ai.tracker")

_ID_PREFIX = {"person": "PERSON"}
_ID_PREFIX.update({cls: "VEHICLE" for cls in VEHICLE_CLASSES})

_MOVE_EPSILON = 3.0  # px before an object is considered "moved"


@dataclass(slots=True)
class TrackedObject:
    track_id: str
    class_name: str
    category: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    first_seen: datetime
    last_seen: datetime
    last_moved_at: datetime
    frame_count: int = 1
    history: list[tuple[float, float]] = field(default_factory=list)
    lost_frames: int = 0

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def stationary_seconds(self) -> float:
        return max(0.0, (self.last_seen - self.last_moved_at).total_seconds())

    @property
    def age_seconds(self) -> float:
        return max(0.0, (self.last_seen - self.first_seen).total_seconds())

    @property
    def aspect_ratio(self) -> float:
        h = abs(self.y2 - self.y1)
        w = abs(self.x2 - self.x1)
        return (h / w) if w > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "bbox": [round(self.x1, 1), round(self.y1, 1), round(self.x2, 1), round(self.y2, 1)],
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "stationary_seconds": round(self.stationary_seconds, 1),
        }


def _iou(a: Detection, b: TrackedObject) -> float:
    ax1, ay1, ax2, ay2 = a.x1, a.y1, a.x2, a.y2
    bx1, by1, bx2, by2 = b.x1, b.y1, b.x2, b.y2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1) * (by2 - by1))
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class Tracker:
    """Tracks objects between consecutive frames. Per-camera instance."""

    def __init__(
        self,
        camera_id: str,
        iou_threshold: float = 0.25,
        max_lost_frames: int = 30,
    ) -> None:
        self.camera_id = camera_id
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.objects: list[TrackedObject] = []
        self._counters: dict[str, int] = {}

    def _next_id(self, class_name: str) -> str:
        prefix = _ID_PREFIX.get(class_name, "OBJECT")
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix} #{self._counters[prefix]:03d}"

    def update(self, detections: list[Detection], timestamp: datetime) -> list[TrackedObject]:
        now = timestamp or datetime.now(timezone.utc)

        matched_prev: set[int] = set()
        matched_det: set[int] = set()

        dets = sorted(detections, key=lambda d: d.confidence, reverse=True)

        # Greedy IoU matching.
        for i, det in enumerate(dets):
            best_j, best_iou = -1, self.iou_threshold
            for j, obj in enumerate(self.objects):
                if j in matched_prev:
                    continue
                iou = _iou(det, obj)
                if iou > best_iou:
                    best_iou = iou
                    best_j = j
            if best_j >= 0:
                matched_prev.add(best_j)
                matched_det.add(i)
                obj = self.objects[best_j]
                _advance(obj, det, now)

        # Births.
        for i, det in enumerate(dets):
            if i in matched_det:
                continue
            new_obj = self._spawn(det, now)
            self.objects.append(new_obj)

        # Loss tracking.
        for j, obj in enumerate(self.objects):
            if j in matched_prev:
                obj.lost_frames = 0
            else:
                obj.lost_frames += 1

        self.objects = [o for o in self.objects if o.lost_frames <= self.max_lost_frames]
        return list(self.objects)

    def _spawn(self, det: Detection, now: datetime) -> TrackedObject:
        obj = TrackedObject(
            track_id=self._next_id(det.class_name),
            class_name=det.class_name,
            category=det.category,
            confidence=det.confidence,
            x1=det.x1,
            y1=det.y1,
            x2=det.x2,
            y2=det.y2,
            first_seen=now,
            last_seen=now,
            last_moved_at=now,
        )
        center = obj.center
        obj.history.append((center[0], center[1], obj.aspect_ratio))
        return obj

    @property
    def count(self) -> int:
        return len(self.objects)


def _advance(obj: TrackedObject, det: Detection, now: datetime) -> None:
    prev = obj.center
    obj.x1, obj.y1, obj.x2, obj.y2 = det.x1, det.y1, det.x2, det.y2
    obj.confidence = det.confidence
    obj.last_seen = now
    obj.frame_count += 1
    center = obj.center
    distance = math.hypot(center[0] - prev[0], center[1] - prev[1])
    if distance > _MOVE_EPSILON:
        obj.last_moved_at = now
    obj.history.append((center[0], center[1], obj.aspect_ratio))
    if len(obj.history) > 120:
        obj.history.pop(0)
    if det.track_id and det.track_id != obj.track_id:
        pass  # keep our own stable tracker id


class TrackerRegistry:
    """Holds one Tracker per camera (tracking state is per-camera)."""

    def __init__(self) -> None:
        self._trackers: dict[str, Tracker] = {}
        self._lock = threading.Lock()

    def get(self, camera_id: str | None) -> Tracker:
        key = camera_id or "default"
        with self._lock:
            if key not in self._trackers:
                self._trackers[key] = Tracker(key)
            return self._trackers[key]

    def reset(self, camera_id: str | None = None) -> None:
        with self._lock:
            if camera_id is None:
                self._trackers.clear()
            else:
                self._trackers.pop(camera_id, None)