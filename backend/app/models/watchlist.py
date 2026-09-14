"""Watchlist entity model — vehicles and persons of interest."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WatchlistEntity(Base):
    __tablename__ = "watchlist_entities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium", nullable=False, index=True)

    vehicle_registration: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vehicle_make: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_colour: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plate_normalized: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    person_age_range: Mapped[str | None] = mapped_column(String(16), nullable=True)
    person_gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    person_clothing: Mapped[str | None] = mapped_column(String(256), nullable=True)
    person_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    aliases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reference_images: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
