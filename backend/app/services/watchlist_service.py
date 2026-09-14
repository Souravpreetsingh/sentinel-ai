"""Watchlist service layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.core.logging import get_logger
from app.models import WatchlistEntity
from app.schemas.watchlist import WatchlistCreate, WatchlistUpdate
from app.services.plates import normalize_plate

logger = get_logger("services.watchlist")


def next_watchlist_id(db: Session) -> str:
    rows = db.query(WatchlistEntity.id).order_by(WatchlistEntity.id.desc()).limit(1).all()
    if not rows:
        return "WL-5001"
    nums = []
    for (cid,) in rows:
        parts = cid.split("-", 1)
        if len(parts) == 2:
            try:
                nums.append(int(parts[1]))
            except ValueError:
                pass
    return f"WL-{max(nums, default=0) + 1}"


def list_entities(
    db: Session,
    category: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    query: str | None = None,
    limit: int = 500,
) -> list[WatchlistEntity]:
    q = db.query(WatchlistEntity)
    if category:
        q = q.filter(WatchlistEntity.category == category)
    if status:
        q = q.filter(WatchlistEntity.status == status)
    if priority:
        q = q.filter(WatchlistEntity.priority == priority)
    if query:
        like = f"%{query}%"
        q = q.filter(
            (WatchlistEntity.name.ilike(like))
            | (WatchlistEntity.vehicle_registration.ilike(like))
            | (WatchlistEntity.plate_normalized.ilike(like))
        )
    return q.order_by(WatchlistEntity.updated_at.desc()).limit(limit).all()


def get_entity(db: Session, entity_id: str) -> WatchlistEntity:
    ent = db.query(WatchlistEntity).filter(WatchlistEntity.id == entity_id).first()
    if ent is None:
        raise not_found("WatchlistEntity", entity_id)
    return ent


def create_entity(db: Session, data: WatchlistCreate) -> WatchlistEntity:
    now = datetime.now(timezone.utc)
    ent = WatchlistEntity(
        id=next_watchlist_id(db),
        category=data.category,
        name=data.name,
        status=data.status,
        priority=data.priority,
        vehicle_registration=data.vehicle_registration,
        vehicle_type=data.vehicle_type,
        vehicle_make=data.vehicle_make,
        vehicle_model=data.vehicle_model,
        vehicle_colour=data.vehicle_colour,
        plate_normalized=normalize_plate(data.vehicle_registration) or None,
        person_age_range=data.person_age_range,
        person_gender=data.person_gender,
        person_clothing=data.person_clothing,
        person_remarks=data.person_remarks,
        aliases=data.aliases,
        reference_images=data.reference_images,
        notes=data.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(ent)
    db.commit()
    db.refresh(ent)
    _broadcast("watchlist.created", ent)
    return ent


def update_entity(db: Session, entity_id: str, data: WatchlistUpdate) -> WatchlistEntity:
    ent = get_entity(db, entity_id)
    update_data = data.model_dump(exclude_unset=True)
    if "vehicle_registration" in update_data:
        update_data["plate_normalized"] = normalize_plate(update_data["vehicle_registration"]) or None
    for field, value in update_data.items():
        if hasattr(ent, field):
            setattr(ent, field, value)
    ent.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ent)
    _broadcast("watchlist.updated", ent)
    return ent


def delete_entity(db: Session, entity_id: str) -> None:
    ent = get_entity(db, entity_id)
    db.delete(ent)
    db.commit()
    _broadcast("watchlist.deleted", {"id": entity_id})


def _broadcast(event: str, ent: WatchlistEntity) -> None:
    from app.websocket import manager
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if not loop.is_running():
        return
    payload = {
        "id": ent.id,
        "category": ent.category,
        "name": ent.name,
        "priority": ent.priority,
        "status": ent.status,
        "vehicle_registration": ent.vehicle_registration or "",
        "plate_normalized": ent.plate_normalized or "",
    }
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(event, payload), loop)
    except RuntimeError:
        pass