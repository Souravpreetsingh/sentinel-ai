"""Incident service layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate

if TYPE_CHECKING:
    from app.ai.types import DetectionEvent
    from app.models import Camera

_EVENT_DESCRIPTIONS = {
    "restricted_zone_entry": "Person entered a restricted zone.",
    "crowd_density_high": "High crowd density detected.",
    "abandoned_object": "Possible abandoned object (AI heuristic, not certain).",
    "vehicle_stopped": "Vehicle stopped for an extended period.",
    "possible_person_fall": "Possible person fall (heuristic, not a medical determination).",
    "traffic_congestion": "AI-estimated traffic congestion.",
    "accident": "Possible accident detected.",
}


def next_incident_id(db: Session) -> str:
    incs = db.query(Incident.id).order_by(desc(Incident.id)).limit(1).all()
    if not incs:
        return "INC-1001"
    nums = []
    for (cid,) in incs:
        parts = cid.split("-", 1)
        if len(parts) == 2:
            try:
                nums.append(int(parts[1]))
            except ValueError:
                pass
    nxt = max(nums, default=0) + 1
    return f"INC-{nxt}"


def list_incidents(
    db: Session,
    severity: str | None = None,
    status: str | None = None,
    camera_id: str | None = None,
    limit: int = 200,
) -> list[Incident]:
    q = db.query(Incident)
    if severity:
        q = q.filter(Incident.severity == severity)
    if status:
        q = q.filter(Incident.status == status)
    if camera_id:
        q = q.filter(Incident.camera_id == camera_id)
    return q.order_by(desc(Incident.detected_at)).limit(limit).all()


def get_incident(db: Session, incident_id: str) -> Incident:
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if inc is None:
        raise not_found("Incident", incident_id)
    return inc


def create_incident(db: Session, data: IncidentCreate, incident_id: str | None = None) -> Incident:
    inc = Incident(
        id=incident_id or next_incident_id(db),
        type=data.type,
        severity=data.severity,
        camera_id=data.camera_id,
        location=data.location,
        status=data.status,
        detected_at=data.detected_at or datetime.now(timezone.utc),
        duration=data.duration,
        confidence=data.confidence,
        description=data.description,
        assigned_to=data.assigned_to,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    _broadcast_incident("incident_created", inc)
    _broadcast_incident("incident.created", inc)
    return inc


def update_incident(db: Session, incident_id: str, data: IncidentUpdate) -> Incident:
    inc = get_incident(db, incident_id)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return inc
    prev_status = inc.status
    for field, value in update_data.items():
        if hasattr(inc, field):
            setattr(inc, field, value)
    inc.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inc)
    if inc.status != prev_status:
        _broadcast_incident("incident_updated", inc)
        _broadcast_incident("incident.updated", inc)
    return inc


def create_from_event(
    db: Session,
    event: DetectionEvent,
    camera: Camera | None = None,
) -> Incident | None:
    """Create an Incident from a pipeline DetectionEvent (cooldown-limited).

    Incident fields: id, type, camera_id, timestamp, severity, confidence,
    track_ids, metadata. No officer is ever auto-assigned.
    """
    track_ids = [o.get("track_id") for o in event.objects if o.get("track_id")]
    metadata = dict(event.metadata or {})
    metadata["event_id"] = event.event_id
    metadata["track_ids"] = track_ids
    metadata["source"] = "ai.video_pipeline"
    if camera is not None:
        metadata["location"] = camera.location

    inc = Incident(
        id=next_incident_id(db),
        type=event.event_type,
        severity=event.severity,
        camera_id=event.camera_id,
        location=camera.location if camera is not None else None,
        status="open",
        detected_at=event.timestamp,
        confidence=round(event.confidence, 3),
        description=_EVENT_DESCRIPTIONS.get(
            event.event_type, f"AI detection: {event.event_type}."
        ),
        assigned_to=None,
        metadata_json=metadata,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    _broadcast_incident("incident_created", inc)
    _broadcast_incident("incident.created", inc)
    return inc


def _broadcast_incident(event: str, inc: Incident) -> None:
    from app.websocket import manager
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if not loop.is_running():
        return
    payload = {
        "incident_id": inc.id,
        "type": inc.type,
        "severity": inc.severity,
        "status": inc.status,
        "camera_id": inc.camera_id,
        "location": inc.location,
        "confidence": inc.confidence,
    }
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(event, payload), loop)
    except RuntimeError:
        pass