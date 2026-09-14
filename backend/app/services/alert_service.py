"""Alert service — watchlist match alerts with configurable deduplication.

Dedup contract (Phase 6, §10): the same entity + same camera + same watchlist
record within ``alert_cooldown_seconds`` produces ONE alert. Movement to
another camera updates tracking/history instead of blindly creating duplicates.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.core.logging import get_logger
from app.models import Alert, Camera
from app.schemas.alert import AlertUpdate
from app.websocket.manager import manager

logger = get_logger("services.alert")


def next_alert_id(db: Session) -> str:
    rows = db.query(Alert.id).order_by(Alert.id.desc()).limit(1).all()
    if not rows:
        return "ALR-9001"
    nums = []
    for (cid,) in rows:
        parts = cid.split("-", 1)
        if len(parts) == 2:
            try:
                nums.append(int(parts[1]))
            except ValueError:
                pass
    return f"ALR-{max(nums, default=0) + 1}"


def list_alerts(
    db: Session,
    status: str | None = None,
    severity: str | None = None,
    camera_id: str | None = None,
    watchlist_id: str | None = None,
    tracking_id: str | None = None,
    since: datetime | None = None,
    limit: int = 200,
) -> list[Alert]:
    q = db.query(Alert)
    if status:
        q = q.filter(Alert.status == status)
    if severity:
        q = q.filter(Alert.severity == severity)
    if camera_id:
        q = q.filter(Alert.camera_id == camera_id)
    if watchlist_id:
        q = q.filter(Alert.watchlist_id == watchlist_id)
    if tracking_id:
        q = q.filter(Alert.tracking_id == tracking_id)
    if since:
        q = q.filter(Alert.detected_at >= since)
    return q.order_by(Alert.detected_at.desc()).limit(limit).all()


def get_alert(db: Session, alert_id: str) -> Alert:
    al = db.query(Alert).filter(Alert.id == alert_id).first()
    if al is None:
        raise not_found("Alert", alert_id)
    return al


def recent_deduped(db: Session, dedup_key: str, cooldown_seconds: float) -> Alert | None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(0, cooldown_seconds))
    return (
        db.query(Alert)
        .filter(Alert.dedup_key == dedup_key, Alert.detected_at >= cutoff)
        .order_by(Alert.detected_at.desc())
        .first()
    )


def create_alert(
    db: Session,
    *,
    severity: str,
    watchlist_id: str | None,
    camera_id: str | None,
    entity_name: str,
    entity_category: str,
    entity_identifier: str | None,
    match_type: str,
    confidence: float,
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    detection_id: str | None = None,
    tracking_id: str | None = None,
    evidence_id: str | None = None,
    snapshot_path: str | None = None,
    detection_metadata: dict | None = None,
    dedup_key: str | None = None,
    detected_at: datetime | None = None,
    return_existing: bool = True,
) -> tuple[Alert | None, bool]:
    """Create an alert with dedup support.

    Returns ``(alert, created)``. When ``return_existing`` is true and a recent
    alert exists for the same ``dedup_key``, the existing alert is returned with
    ``created=False`` instead of creating a duplicate.
    """
    from app.core.config import get_settings

    cooldown = get_settings().alert_cooldown_seconds
    if dedup_key:
        existing = recent_deduped(db, dedup_key, cooldown)
        if existing is not None:
            if return_existing:
                return existing, False
            return None, False

    now = datetime.now(timezone.utc)

    alert = Alert(
        id=next_alert_id(db),
        severity=severity,
        status="new",
        watchlist_id=watchlist_id,
        camera_id=camera_id,
        detection_id=detection_id,
        tracking_id=tracking_id,
        evidence_id=evidence_id,
        entity_name=entity_name,
        entity_category=entity_category,
        entity_identifier=entity_identifier,
        match_type=match_type,
        confidence=round(confidence, 4),
        location=location,
        latitude=latitude,
        longitude=longitude,
        snapshot_path=snapshot_path,
        detection_metadata=detection_metadata or {},
        dedup_key=dedup_key,
        detected_at=detected_at or now,
        created_at=now,
        updated_at=now,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    logger.info(
        "alert created id=%s severity=%s status=new watchlist=%s camera=%s entity=%r match_type=%s confidence=%.4f evidence=%s",
        alert.id, alert.severity, alert.watchlist_id, alert.camera_id,
        alert.entity_identifier, alert.match_type, alert.confidence, alert.evidence_id,
    )
    _broadcast("alert.created", alert)
    return alert, True


def update_alert(db: Session, alert_id: str, data: AlertUpdate) -> Alert:
    alert = get_alert(db, alert_id)
    update_data = data.model_dump(exclude_unset=True)
    now = datetime.now(timezone.utc)
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status in ("acknowledged", "investigating") and not alert.acknowledged_at:
            alert.acknowledged_at = now
        if new_status in ("resolved", "false_positive") and not alert.resolved_at:
            alert.resolved_at = now
    for field, value in update_data.items():
        if hasattr(alert, field):
            setattr(alert, field, value)
    alert.updated_at = now
    db.commit()
    db.refresh(alert)
    _broadcast("alert.updated", alert)
    return alert


def _broadcast(event: str, alert: Alert) -> None:
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if not loop.is_running():
        return
    payload = {
        "id": alert.id,
        "severity": alert.severity,
        "status": alert.status,
        "watchlist_id": alert.watchlist_id,
        "camera_id": alert.camera_id,
        "entity_name": alert.entity_name,
        "entity_category": alert.entity_category,
        "entity_identifier": alert.entity_identifier,
        "match_type": alert.match_type,
        "confidence": alert.confidence,
        "location": alert.location,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "evidence_id": alert.evidence_id,
        "tracking_id": alert.tracking_id,
        "detected_at": alert.detected_at.isoformat(),
        "detection_metadata": alert.detection_metadata,
    }
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(event, payload), loop)
    except RuntimeError:
        pass