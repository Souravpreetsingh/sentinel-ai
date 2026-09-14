"""GIS service — camera/event layers, vehicle routes, spatial search probes.

The queries are deliberately kept database-agnostic (SQLAlchemy Core) so the
same code runs on SQLite in the demo and on a spatially-indexed PostgreSQL
(PostGIS) deployment for the 80k-camera model.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Alert, Camera, MovementEvent, VehicleTrack


def camera_locations(db: Session) -> list[dict]:
    """All cameras with coordinates (online/active first)."""
    order = {
        "ACTIVE": 0,
        "DEGRADED": 1,
        "MAINTENANCE": 2,
        "OFFLINE": 3,
        "DISABLED": 4,
    }
    cams = db.query(Camera).all()
    out = []
    for c in cams:
        if c.latitude is None or c.longitude is None:
            continue
        out.append({
            "id": c.id,
            "name": c.name,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "status": c.status,
            "lifecycle": c.lifecycle,
            "district": c.district,
            "zone": c.zone,
            "road": c.road,
            "ai_enabled": c.ai_enabled,
            "last_seen": c.last_seen.isoformat() if c.last_seen else None,
            "detections": c.detections or {},
        })
    out.sort(key=lambda d: order.get(d["lifecycle"], 5))
    return out


def event_locations(db: Session, limit: int = 500) -> list[dict]:
    """Recent alerts with coordinates."""
    rows = (
        db.query(Alert)
        .filter(Alert.latitude.isnot(None), Alert.longitude.isnot(None))
        .order_by(Alert.detected_at.desc())
        .limit(limit)
        .all()
    )
    cams = {c.id: c.name for c in db.query(Camera.id, Camera.name).all()}
    return [
        {
            "id": a.id,
            "kind": "alert",
            "severity": a.severity,
            "status": a.status,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "camera_id": a.camera_id,
            "camera_name": cams.get(a.camera_id) if a.camera_id else None,
            "title": a.entity_name or a.match_type or "Alert",
            "timestamp": a.detected_at.isoformat(),
            "confidence": a.confidence,
        }
        for a in rows
    ]


def vehicle_route(db: Session, entity_identifier: str) -> dict | None:
    """Chronological route for an entity (from MovementEvents)."""
    track = (
        db.query(VehicleTrack)
        .filter(VehicleTrack.entity_identifier == entity_identifier)
        .order_by(VehicleTrack.last_seen.desc())
        .first()
    )
    if track is None:
        return None
    return _track_route(db, track)


def _track_route(db: Session, track: VehicleTrack) -> dict:
    moves = (
        db.query(MovementEvent)
        .filter(MovementEvent.track_id == track.id)
        .order_by(MovementEvent.detected_at.asc())
        .all()
    )
    cams = {c.id: c.name for c in db.query(Camera.id, Camera.name).all()}
    points = [
        {
            "camera_id": m.camera_id,
            "camera_name": cams.get(m.camera_id) if m.camera_id else None,
            "latitude": m.latitude,
            "longitude": m.longitude,
            "timestamp": m.detected_at.isoformat(),
            "confidence": m.confidence,
        }
        for m in moves
        if m.latitude is not None and m.longitude is not None
    ]
    # Always include the current position even before any movement row exists.
    if not points and track.current_latitude is not None:
        points = [{
            "camera_id": track.current_camera_id,
            "camera_name": cams.get(track.current_camera_id) if track.current_camera_id else None,
            "latitude": track.current_latitude,
            "longitude": track.current_longitude,
            "timestamp": track.last_seen.isoformat(),
            "confidence": track.confidence,
        }]
    return {
        "track_id": track.id,
        "entity_identifier": track.entity_identifier,
        "watchlist_id": track.watchlist_id,
        "status": track.status,
        "first_seen": track.first_seen.isoformat(),
        "last_seen": track.last_seen.isoformat(),
        "points": points,
    }


def summary(db: Session) -> dict:
    camera_total = db.query(func.count(Camera.id)).scalar() or 0
    camera_online = db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0
    camera_offline = camera_total - camera_online
    alert_total = db.query(func.count(Alert.id)).scalar() or 0
    tracked = db.query(func.count(VehicleTrack.id)).filter(VehicleTrack.status == "active").scalar() or 0
    return {
        "camera_total": camera_total,
        "camera_online": camera_online,
        "camera_offline": camera_offline,
        "alert_total": alert_total,
        "tracked_vehicles": tracked,
    }