"""Cross-camera vehicle tracking models.

``VehicleTrack`` is the persisted composite track for an entity of interest;
``MovementEvent`` records each camera hop along the route with evidence and
confidence. Together they answer "where was the vehicle / what route / which
cameras saw it / when was it last seen".
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VehicleTrack(Base):
    __tablename__ = "vehicle_tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    watchlist_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("watchlist_entities.id"), nullable=True, index=True
    )
    entity_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    current_camera_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    hop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)

    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class MovementEvent(Base):
    __tablename__ = "movement_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    track_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vehicle_tracks.id"), nullable=True, index=True
    )
    camera_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("cameras.id"), nullable=True, index=True
    )
    detection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    entity_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )