"""Unified investigation search across detections / alerts / tracks /
watchlist / cameras / evidence.

Answers the Phase 6 queries: "where was this vehicle", "which cameras saw it",
"What route", "when last seen", "nearby alerts".
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Alert, Camera, Detection, Evidence, MovementEvent, VehicleTrack, WatchlistEntity
from app.services.plates import normalize_plate


def _like(term: str) -> str:
    return f"%{term}%"


def search(
    db: Session,
    query: str,
    *,
    camera_id: str | None = None,
    district: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    tracking_id: str | None = None,
    watchlist_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 50,
) -> dict:
    q = (query or "").strip()
    norm = normalize_plate(q)
    out: list[dict] = []

    cams = {c.id: c for c in db.query(Camera).all()} if camera_id or query else {}

    def time_in_range(ts: datetime | None) -> bool:
        if ts is None:
            return True
        if start and ts < start:
            return False
        if end and ts > end:
            return False
        return True

    # --- Cameras ------------------------------------------------------------
    if not camera_id and q:
        like = _like(q)
        cam_rows = (
            db.query(Camera)
            .filter(
                or_(
                    Camera.id.ilike(like),
                    Camera.name.ilike(like),
                    Camera.location.ilike(like),
                    Camera.vendor.ilike(like),
                    Camera.district.ilike(like),
                    Camera.zone.ilike(like),
                )
            )
            .limit(8)
            .all()
        )
        for c in cam_rows:
            out.append({
                "kind": "camera",
                "id": c.id,
                "title": c.name,
                "subtitle": ",".join(x for x in [c.district, c.zone, c.road] if x) or c.location,
                "timestamp": None,
                "camera_id": c.id,
                "camera_name": c.name,
                "severity": None,
                "status": c.status,
                "confidence": None,
                "location": c.location,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "extra": {"lifecycle": c.lifecycle, "vendor": c.vendor},
            })

    # --- Watchlist ----------------------------------------------------------
    wl_query = db.query(WatchlistEntity)
    if watchlist_id:
        wl_query = wl_query.filter(WatchlistEntity.id == watchlist_id)
    elif q:
        like = _like(q)
        wl_query = wl_query.filter(
            or_(
                WatchlistEntity.name.ilike(like),
                WatchlistEntity.vehicle_registration.ilike(like),
                WatchlistEntity.plate_normalized.ilike(like),
                WatchlistEntity.id.ilike(like),
            )
        )
    for w in wl_query.order_by(WatchlistEntity.updated_at.desc()).limit(10).all():
        out.append({
            "kind": "watchlist",
            "id": w.id,
            "title": w.name,
            "subtitle": f"{w.category} · {w.plate_normalized or w.vehicle_registration or 'entity'}",
            "timestamp": None,
            "camera_id": None,
            "camera_name": None,
            "severity": w.priority,
            "status": w.status,
            "confidence": None,
            "location": None,
            "latitude": None,
            "longitude": None,
            "extra": {"category": w.category, "vehicle_registration": w.vehicle_registration},
        })

    # --- Alerts -------------------------------------------------------------
    al_q = db.query(Alert)
    if tracking_id:
        al_q = al_q.filter(Alert.tracking_id == tracking_id)
    if severity:
        al_q = al_q.filter(Alert.severity == severity)
    if watchlist_id:
        al_q = al_q.filter(Alert.watchlist_id == watchlist_id)
    if camera_id:
        if event_type:  # re-use camera filter as "matches partial"
            pass
        al_q = al_q.filter(Alert.camera_id == camera_id)
    elif q:
        like = _like(q)
        al_q = al_q.filter(
            or_(
                Alert.entity_name.ilike(like),
                Alert.entity_identifier.ilike(like),
                Alert.location.ilike(like),
                Alert.id.ilike(like),
            )
        )
    for a in al_q.order_by(Alert.detected_at.desc()).limit(10).all():
        if not time_in_range(a.detected_at):
            continue
        cam = cams.get(a.camera_id)
        out.append({
            "kind": "alert",
            "id": a.id,
            "title": f"{a.entity_name} ({a.match_type})",
            "subtitle": f"{a.entity_category} · {a.entity_identifier or 'entity'} seen at {a.camera_id or '?'}",
            "timestamp": a.detected_at,
            "camera_id": a.camera_id,
            "camera_name": cam.name if cam else None,
            "severity": a.severity,
            "status": a.status,
            "confidence": a.confidence,
            "location": a.location,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "extra": {"evidence_id": a.evidence_id, "tracking_id": a.tracking_id, "match_type": a.match_type},
        })

    # --- Detections ---------------------------------------------------------
    det_q = db.query(Detection)
    if camera_id:
        det_q = det_q.filter(Detection.camera_id == camera_id)
    if event_type:
        det_q = det_q.filter(Detection.class_name == event_type)
    elif q:
        det_q = det_q.filter(
            or_(
                Detection.track_id.ilike(_like(q)),
                Detection.camera_id.ilike(_like(q)),
            )
        )
    for d in det_q.order_by(Detection.detected_at.desc()).limit(10).all():
        if not time_in_range(d.detected_at):
            continue
        cam = cams.get(d.camera_id)
        out.append({
            "kind": "detection",
            "id": d.id or "",
            "title": f"{d.class_name} detected",
            "subtitle": f"{d.confidence * 100:.0f}% · track {d.track_id or 'unassigned'}",
            "timestamp": d.detected_at,
            "camera_id": d.camera_id,
            "camera_name": cam.name if cam else None,
            "severity": None,
            "status": None,
            "confidence": d.confidence,
            "location": cam.location if cam else None,
            "latitude": cam.latitude if cam else None,
            "longitude": cam.longitude if cam else None,
            "extra": {"class_name": d.class_name, "track_id": d.track_id},
        })

    # --- Tracks -------------------------------------------------------------
    tr_q = db.query(VehicleTrack)
    if tracking_id:
        tr_q = tr_q.filter(VehicleTrack.id == tracking_id)
    if camera_id:
        tr_q = tr_q.filter(VehicleTrack.current_camera_id == camera_id)
    if watchlist_id:
        tr_q = tr_q.filter(VehicleTrack.watchlist_id == watchlist_id)
    elif q:
        tr_q = tr_q.filter(
            or_(
                VehicleTrack.entity_identifier.ilike(_like(q)),
                VehicleTrack.id.ilike(_like(q)),
            )
        )
    for t in tr_q.order_by(VehicleTrack.last_seen.desc()).limit(10).all():
        if not time_in_range(t.last_seen):
            continue
        cam = cams.get(t.current_camera_id)
        out.append({
            "kind": "track",
            "id": t.id,
            "title": f"Track {t.entity_identifier or t.id}",
            "subtitle": f"{t.hop_count} camera hops · last at {t.current_camera_id or '?'}",
            "timestamp": t.last_seen,
            "camera_id": t.current_camera_id,
            "camera_name": cam.name if cam else None,
            "severity": None,
            "status": t.status,
            "confidence": t.confidence,
            "location": None,
            "latitude": t.current_latitude,
            "longitude": t.current_longitude,
            "extra": {"hop_count": t.hop_count},
        })

    # --- Evidence -----------------------------------------------------------
    if q:
        ev_q = (
            db.query(Evidence)
            .filter(
                or_(
                    Evidence.title.ilike(_like(q)),
                    Evidence.id.ilike(_like(q)),
                    Evidence.camera_id.ilike(_like(q)),
                )
            )
            .order_by(Evidence.created_at.desc())
            .limit(6)
            .all()
        )
        for e in ev_q:
            cam = cams.get(e.camera_id)
            out.append({
                "kind": "evidence",
                "id": e.id,
                "title": e.title or e.id,
                "subtitle": f"{e.type} · {e.verification_status}",
                "timestamp": e.captured_at,
                "camera_id": e.camera_id,
                "camera_name": cam.name if cam else None,
                "severity": None,
                "status": e.verification_status,
                "confidence": None,
                "location": None,
                "latitude": None,
                "longitude": None,
                "extra": {"verified": e.verification_status == "verified"},
            })

    out.sort(key=lambda r: (r["timestamp"] is None, -(r["timestamp"].timestamp() if r["timestamp"] else 0)))

    facets = {"detections": 0, "alerts": 0, "tracks": 0, "watchlist": 0, "cameras": 0, "evidence": 0}
    for r in out:
        facets[r["kind"]] = facets.get(r["kind"], 0) + 1

    return {
        "query": q,
        "total": len(out),
        "results": out[:limit],
        "facets": facets,
    }


def nearby_alerts(db: Session, latitude: float, longitude: float, radius_km: float = 5.0, limit: int = 20) -> list[dict]:
    """Simple equirectangular distance probe (accurate enough for <100 km).

    At scale this is replaced by a PostGIS ``ST_DWithin`` index scan.
    """
    import math

    def dist_km(a_lat: float, a_lon: float) -> float:
        dlat = math.radians(latitude - a_lat)
        dlon = math.radians(longitude - a_lon)
        x = dlon * math.cos(math.radians((latitude + a_lat) / 2.0))
        return math.hypot(x, dlat) * 6371.0

    rows = (
        db.query(Alert)
        .filter(Alert.latitude.isnot(None), Alert.longitude.isnot(None))
        .order_by(Alert.detected_at.desc())
        .limit(500)
        .all()
    )
    near = []
    for a in rows:
        d = dist_km(a.latitude, a.longitude)
        if d <= radius_km:
            near.append({
                "id": a.id,
                "severity": a.severity,
                "status": a.status,
                "entity_name": a.entity_name,
                "detected_at": a.detected_at.isoformat(),
                "latitude": a.latitude,
                "longitude": a.longitude,
                "distance_km": round(d, 2),
            })
    return sorted(near, key=lambda r: r["distance_km"])[:limit]