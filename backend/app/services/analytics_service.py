"""Analytics service - computed from real persisted detection/incident records.

All counts, categories and time-series are derived from the database so they
survive restarts, avoid duplicate/phantom entries, and return valid empty
values when no events have been recorded yet.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Camera, Detection, Incident

PERSON_CLASSES = {"person", "human", "pedestrian"}
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "vehicle"}

WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _count(db: Session) -> int:
    return db.query(func.count(Detection.id)).scalar() or 0


def _count_people(db: Session) -> int:
    return (
        db.query(func.count(Detection.id))
        .filter(Detection.class_name.in_(PERSON_CLASSES))
        .scalar()
        or 0
    )


def _count_vehicles(db: Session) -> int:
    return (
        db.query(func.count(Detection.id))
        .filter(Detection.class_name.in_(VEHICLE_CLASSES))
        .scalar()
        or 0
    )


def _category_counts(db: Session, limit: int = 12) -> list[dict]:
    rows = (
        db.query(Detection.class_name, func.count(Detection.id))
        .group_by(Detection.class_name)
        .order_by(func.count(Detection.id).desc())
        .all()
    )
    return [
        {"category": name.replace("_", " ").title(), "count": count}
        for (name, count) in rows[:limit]
        if name
    ]


def _hourly(db: Session) -> list[dict]:
    det_rows = (
        db.query(
            func.strftime("%H", Detection.detected_at).label("hour"),
            func.count(Detection.id).label("total"),
            func.count(Detection.id).filter(Detection.class_name.in_(PERSON_CLASSES)).label("pedestrians"),
            func.count(Detection.id).filter(Detection.class_name.in_(VEHICLE_CLASSES)).label("vehicles"),
        )
        .group_by("hour")
        .all()
    )
    inc_rows = (
        db.query(
            func.strftime("%H", Incident.created_at).label("hour"),
            func.count(Incident.id).label("incidents"),
        )
        .group_by("hour")
        .all()
    )
    det_by_hour = {int(h): (int(p), int(v)) for (h, _t, p, v) in det_rows}
    inc_by_hour = {int(h): int(c) for (h, c) in inc_rows}
    out = []
    for hour in range(24):
        ped, veh = det_by_hour.get(hour, (0, 0))
        out.append(
            {
                "hour": f"{hour:02d}:00",
                "pedestrians": ped,
                "vehicles": veh,
                "incidents": inc_by_hour.get(hour, 0),
            }
        )
    return out


def _weekly(db: Session) -> list[dict]:
    det_rows = (
        db.query(
            func.strftime("%w", Detection.detected_at).label("day"),
            func.count(Detection.id).label("detections"),
        )
        .group_by("day")
        .all()
    )
    inc_rows = (
        db.query(
            func.strftime("%w", Incident.created_at).label("day"),
            func.count(Incident.id).label("incidents"),
            func.count(Incident.id).filter(Incident.status == "resolved").label("resolved"),
        )
        .group_by("day")
        .all()
    )
    # strftime('%w') is 0=Sunday..6=Saturday.
    det_by_day = {int(h): int(c) for (h, c) in det_rows}
    inc_by_day = {int(h): (int(c), int(r)) for (h, c, r) in inc_rows}
    out = []
    for idx, name in enumerate(WEEKDAY_ORDER):
        dow = (idx + 1) % 7  # Monday(1)..Sunday(0)
        incidents, resolved = inc_by_day.get(dow, (0, 0))
        out.append(
            {
                "day": name,
                "detections": det_by_day.get(dow, 0),
                "incidents": incidents,
                "resolved": resolved,
            }
        )
    return out


def _camera_utilization(db: Session) -> list[dict]:
    rows = (
        db.query(Detection.camera_id, func.count(Detection.id))
        .group_by(Detection.camera_id)
        .all()
    )
    total = sum(count for _, count in rows)
    if not rows or total == 0:
        return []
    out = []
    for camera_id, count in rows:
        if camera_id is None:
            continue
        out.append(
            {
                "cameraId": camera_id,
                "utilization": round(count / total * 100, 1),
                "uptime": 100.0,
            }
        )
    return out


def _model_performance(db: Session) -> dict:
    settings = get_settings()
    avg_conf = (
        db.query(func.avg(Detection.confidence)).scalar() if _count(db) > 0 else None
    )
    is_mock = settings.detector_backend == "mock"
    return {
        "yoloVersion": settings.yolo_model if not is_mock else "mock",
        "averageInference": "N/A (mock)" if is_mock else "N/A",
        "accuracy": round(avg_conf * 100, 1) if avg_conf is not None else 0.0,
        "falsePositiveRate": 0.0,
        "modelsLoaded": 1 if settings.detector_backend != "auto" else 0,
        "gpuMemory": "N/A (CPU mode)",
        "gpuTemp": 0.0,
    }


def overview(db: Session) -> dict:
    cameras_total = db.query(func.count(Camera.id)).scalar() or 0
    cameras_online = db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0
    cameras_warning = db.query(func.count(Camera.id)).filter(Camera.status == "warning").scalar() or 0
    ai_enabled = db.query(func.count(Camera.id)).filter(Camera.ai_enabled == True).scalar() or 0  # noqa: E712
    critical_incidents = db.query(func.count(Incident.id)).filter(Incident.severity == "critical").scalar() or 0
    open_incidents = db.query(func.count(Incident.id)).filter(Incident.status == "open").scalar() or 0

    hourly = _hourly(db)
    weekly = _weekly(db)
    categories = _category_counts(db)

    return {
        "people_detected": _count_people(db),
        "vehicles_detected": _count_vehicles(db),
        "events": _count(db),
        "critical_incidents": critical_incidents,
        "open_incidents": open_incidents,
        "cameras_online": cameras_online,
        "cameras_total": cameras_total,
        "cameras_warning": cameras_warning,
        "ai_enabled_count": ai_enabled,
        "event_categories": categories,
        "hourly_activity": hourly,
        "hourlyTraffic": hourly,
        "weeklyTrend": weekly,
        "topEventTypes": categories[:8],
        "cameraUtilization": _camera_utilization(db),
        "aiModelPerformance": _model_performance(db),
    }


def events(db: Session) -> dict:
    critical_events = db.query(func.count(Incident.id)).filter(Incident.severity == "critical").scalar() or 0
    high_events = db.query(func.count(Incident.id)).filter(Incident.severity == "high").scalar() or 0

    return {
        "total_events": _count(db),
        "event_categories": _category_counts(db),
        "hourly_activity": _hourly(db),
        "critical_events": critical_events,
        "high_severity_events": high_events,
        "weeklyTrend": _weekly(db),
        "topEventTypes": _category_counts(db, 8),
    }


def traffic(db: Session) -> dict:
    hourly = _hourly(db)
    total_p = sum(h["pedestrians"] for h in hourly)
    total_v = sum(h["vehicles"] for h in hourly)
    total_i = sum(h["incidents"] for h in hourly)
    peak_v = max(hourly, key=lambda h: h["vehicles"]) if hourly else {"hour": "00:00"}
    peak_p = max(hourly, key=lambda h: h["pedestrians"]) if hourly else {"hour": "00:00"}

    return {
        "traffic_stats": {
            "total_pedestrians": total_p,
            "total_vehicles": total_v,
            "total_incidents": total_i,
            "peak_vehicles_hour": peak_v.get("hour", "00:00"),
            "peak_pedestrians_hour": peak_p.get("hour", "00:00"),
        },
        "hourlyTraffic": hourly,
        "weeklyTrend": _weekly(db),
        "event_categories": _category_counts(db),
        "hourly_activity": hourly,
    }


def cameras(db: Session) -> dict:
    cameras_total = db.query(func.count(Camera.id)).scalar() or 0
    cameras_online = db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0
    cameras_warning = db.query(func.count(Camera.id)).filter(Camera.status == "warning").scalar() or 0
    ai_enabled = db.query(func.count(Camera.id)).filter(Camera.ai_enabled == True).scalar() or 0  # noqa: E712

    return {
        "cameras_total": cameras_total,
        "cameras_online": cameras_online,
        "cameras_warning": cameras_warning,
        "ai_enabled_count": ai_enabled,
        "cameraUtilization": _camera_utilization(db),
        "camera_utilization": _camera_utilization(db),
        "cameras": [],
    }