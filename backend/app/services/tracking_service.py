"""Cross-camera vehicle tracking service.

A ``VehicleTrack`` aggregates MovementEvents across cameras for one entity of
interest. New detections are re-linked to the most recent active track for the
same entity identifier within ``tracking_reappearance_seconds`` (cross-camera
handoff), otherwise a new track is opened. Movement creates a MovementEvent row
and updates the composite route rather than duplicating alerts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import not_found
from app.core.logging import get_logger
from app.models import Alert, Camera, MovementEvent, VehicleTrack
from app.services.matching import _edits
from app.services.plates import collapse_ocr, normalize_plate

logger = get_logger("services.tracking")


def list_tracks(
    db: Session,
    status: str | None = None,
    watchlist_id: str | None = None,
    entity_identifier: str | None = None,
    limit: int = 100,
) -> list[VehicleTrack]:
    q = db.query(VehicleTrack)
    if status:
        q = q.filter(VehicleTrack.status == status)
    if watchlist_id:
        q = q.filter(VehicleTrack.watchlist_id == watchlist_id)
    if entity_identifier:
        q = q.filter(VehicleTrack.entity_identifier == entity_identifier)
    return q.order_by(VehicleTrack.last_seen.desc()).limit(limit).all()


def get_track(db: Session, track_id: str) -> VehicleTrack:
    tr = db.query(VehicleTrack).filter(VehicleTrack.id == track_id).first()
    if tr is None:
        raise not_found("VehicleTrack", track_id)
    return tr


def _plate_similarity(a: str, b: str) -> float:
    """How likely two plate keys refer to the same physical plate (1.0 = same)."""
    if a == b:
        return 1.0
    if collapse_ocr(a) == collapse_ocr(b):
        return 0.98
    distance = _edits(a, b)
    max_len = max(len(a), len(b), 1)
    return 1.0 - (distance / max_len)


def latest_track_for(
    db: Session,
    entity_identifier: str,
    watchlist_id: str | None = None,
) -> VehicleTrack | None:
    """Most recent live track that plausibly belongs to ``entity_identifier``.

    Re-linking tolerates ANPR OCR drift between cameras: the read plate is
    compared against candidate tracks by exact key, OCR-collapsed key and
    finally Levenshtein similarity (``tracking_link_similarity``). Tracks on the
    same watchlist entity are preferred over look-alike strangers.
    """
    settings = get_settings()
    window = settings.tracking_reappearance_seconds
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window)
    candidates = (
        db.query(VehicleTrack)
        .filter(
            VehicleTrack.status.in_(("active", "triaged")),
            VehicleTrack.last_seen >= cutoff,
        )
        .order_by(VehicleTrack.last_seen.desc())
        .all()
    )
    if not candidates:
        return None
    target = normalize_plate(entity_identifier or "")
    if not target:
        return candidates[0]
    best: VehicleTrack | None = None
    best_score = 0.0
    for tr in candidates:
        ref = normalize_plate(tr.entity_identifier or "")
        if not ref:
            continue
        score = _plate_similarity(target, ref)
        if watchlist_id and tr.watchlist_id == watchlist_id:
            score += 0.05  # same entity of interest wins ties
        if score > best_score:
            best_score = score
            best = tr
    if best is not None and best_score >= settings.tracking_link_similarity:
        return best
    return None


def find_or_create_track(
    db: Session,
    *,
    entity_identifier: str | None,
    watchlist_id: str | None,
    camera_id: str | None,
    latitude: float | None,
    longitude: float | None,
    confidence: float,
    detected_at: datetime | None = None,
    attributes: dict | None = None,
) -> VehicleTrack:
    now = detected_at or datetime.now(timezone.utc)
    track = latest_track_for(db, entity_identifier or "", watchlist_id) if entity_identifier else None
    if track is None:
        track = VehicleTrack(
            id=f"TRK-{uuid.uuid4().hex[:10].upper()}",
            watchlist_id=watchlist_id,
            entity_identifier=entity_identifier,
            first_seen=now,
            last_seen=now,
            current_camera_id=camera_id,
            current_latitude=latitude,
            current_longitude=longitude,
            hop_count=0,
            confidence=confidence,
            status="active",
            attributes=dict(attributes or {}),
            created_at=now,
            updated_at=now,
        )
        db.add(track)
        db.commit()
        db.refresh(track)
        logger.info("Track created %s for entity=%r", track.id, entity_identifier)
    else:
        was_camera = track.current_camera_id
        if was_camera != camera_id:
            track.hop_count += 1
        track.last_seen = now
        track.current_camera_id = camera_id or track.current_camera_id
        track.current_latitude = latitude if latitude is not None else track.current_latitude
        track.current_longitude = longitude if longitude is not None else track.current_longitude
        track.confidence = max(track.confidence, confidence)
        track.updated_at = now
        db.commit()
        db.refresh(track)
        if was_camera and was_camera != camera_id:
            logger.info("Track %s handed off %s -> %s", track.id, was_camera, camera_id)
    return track


def record_movement(
    db: Session,
    *,
    track_id: str,
    camera_id: str | None,
    entity_identifier: str | None,
    latitude: float | None,
    longitude: float | None,
    confidence: float,
    detected_at: datetime | None = None,
    detection_id: str | None = None,
    alert_id: str | None = None,
    evidence_id: str | None = None,
    speed_kmh: float | None = None,
    metadata_json: dict | None = None,
) -> MovementEvent:
    now = detected_at or datetime.now(timezone.utc)
    # Dedup: skip repeated movement rows for the same track+camera+alert (keeps
    # re-runs idempotent while still allowing legitimate repeat movements from
    # different alerts).
    if alert_id is not None:
        dup = (
            db.query(MovementEvent)
            .filter(
                MovementEvent.track_id == track_id,
                MovementEvent.camera_id == camera_id,
                MovementEvent.alert_id == alert_id,
            )
            .first()
        )
        if dup is not None:
            logger.debug(
                "Movement already recorded for track %s camera %s alert %s; skipping duplicate",
                track_id, camera_id, alert_id,
            )
            return dup
    move = MovementEvent(
        id=f"MV-{uuid.uuid4().hex[:10].upper()}",
        track_id=track_id,
        camera_id=camera_id,
        detection_id=detection_id,
        alert_id=alert_id,
        evidence_id=evidence_id,
        entity_identifier=entity_identifier,
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
        confidence=round(confidence, 4),
        metadata_json=metadata_json or {},
        detected_at=now,
        created_at=now,
    )
    db.add(move)
    db.commit()
    db.refresh(move)
    _broadcast("tracking.movement", move)
    return move


def movements_for_track(db: Session, track_id: str, limit: int = 200) -> list[MovementEvent]:
    return (
        db.query(MovementEvent)
        .filter(MovementEvent.track_id == track_id)
        .order_by(MovementEvent.detected_at.asc())
        .limit(limit)
        .all()
    )


def movements_for_entity(db: Session, entity_identifier: str, limit: int = 500) -> list[MovementEvent]:
    return (
        db.query(MovementEvent)
        .filter(MovementEvent.entity_identifier == entity_identifier)
        .order_by(MovementEvent.detected_at.desc())
        .limit(limit)
        .all()
    )


def camera_name_map(db: Session) -> dict[str, str]:
    return {c.id: c.name for c in db.query(Camera.id, Camera.name).all()}


def _broadcast(event: str, move: MovementEvent) -> None:
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    from app.websocket import manager
    payload = {
        "id": move.id,
        "track_id": move.track_id,
        "camera_id": move.camera_id,
        "entity_identifier": move.entity_identifier,
        "latitude": move.latitude,
        "longitude": move.longitude,
        "confidence": move.confidence,
        "detected_at": move.detected_at.isoformat(),
        "alert_id": move.alert_id,
        "evidence_id": move.evidence_id,
    }
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(event, payload), loop)
    except RuntimeError:
        pass