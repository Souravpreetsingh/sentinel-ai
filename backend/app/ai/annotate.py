"""Frame annotation utilities.

Draws bounding boxes, track IDs, class labels, zone polygons, and event
indicators onto an OpenCV frame. Used by AI_DEBUG and optional output video
generation without blocking realtime processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2  # type: ignore
import numpy as np  # type: ignore

if TYPE_CHECKING:
    from app.ai.tracker import TrackedObject
    from app.ai.types import DetectionEvent
    from app.ai.zones import Zone

_COLORS = {
    "person": (0, 255, 0),
    "car": (0, 200, 255),
    "motorcycle": (255, 180, 0),
    "bicycle": (0, 180, 100),
    "bus": (255, 100, 0),
    "truck": (0, 100, 255),
}

_ZONE_COLORS = {
    "restricted": (0, 165, 255),
    "monitoring": (255, 0, 255),
    "traffic": (255, 255, 0),
}

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _color_for(class_name: str) -> tuple[int, int, int]:
    return _COLORS.get(class_name, (200, 200, 200))


def annotate_frame(
    frame: np.ndarray,
    tracked: list[TrackedObject] | None = None,
    zones: list[Zone] | None = None,
    events: list[DetectionEvent] | None = None,
    label_lines: list[str] | None = None,
) -> np.ndarray:
    """Return a copy of *frame* with annotations drawn.

    The original frame is never modified. Zones, objects and event indicators
    are overlaid for visual debugging.
    """
    img = frame.copy()
    tracked = tracked or []
    zones = zones or []
    events = events or []

    # Draw zones (polygons).
    for zone in zones:
        if not zone.enabled or len(zone.points) < 3:
            continue
        pts = np.array(
            [[int(p.x), int(p.y)] for p in zone.points], dtype=np.int32
        )
        color = _ZONE_COLORS.get(zone.zone_type, (200, 200, 200))
        overlay = img.copy()
        cv2.fillPoly(overlay, [pts], (*color, 35))
        cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
        cv2.polylines(img, [pts], True, color, 2)
        cv2.putText(
            img,
            f"{zone.name} [{zone.zone_type}]",
            (int(zone.points[0].x) + 4, max(12, int(zone.points[0].y) - 8)),
            _FONT,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    # Draw tracked objects (boxes + labels).
    for obj in tracked:
        x1, y1, x2, y2 = int(obj.x1), int(obj.y1), int(obj.x2), int(obj.y2)
        color = _color_for(obj.class_name)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"{obj.track_id} {int(obj.confidence * 100)}%"
        (tw, th), _ = cv2.getTextSize(label, _FONT, 0.45, 1)
        cv2.rectangle(img, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, y1), color, -1)
        cv2.putText(
            img, label, (x1 + 3, max(th + 4, y1 - 4)),
            _FONT, 0.45, (0, 0, 0), 1, cv2.LINE_AA,
        )

    # Event indicators (top-right).
    for idx, ev in enumerate(events[:4]):
        txt = f"! {ev.event_type} [{ev.severity}]"
        y = 24 + idx * 22
        (tw, _), _ = cv2.getTextSize(txt, _FONT, 0.5, 1)
        cv2.rectangle(img, (5, y - 16), (11 + tw, y + 2), (0, 0, 200), -1)
        cv2.putText(img, txt, (8, y - 2), _FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Extra diagnostic lines at bottom-left.
    if label_lines:
        for idx, line in enumerate(label_lines[:4]):
            y = img.shape[0] - 8 - idx * 18
            cv2.putText(
                img, line, (8, y), _FONT, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
            )

    return img