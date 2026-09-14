"""Alert model — real-time watchlist match alerts with deduplication."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False, index=True)

    watchlist_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("watchlist_entities.id"), nullable=True, index=True
    )
    camera_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("cameras.id"), nullable=True, index=True
    )
    detection_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tracking_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    entity_name: Mapped[str] = mapped_column(String(256), nullable=False)
    entity_category: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)

    match_type: Mapped[str] = mapped_column(String(16), default="no_match", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    detection_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
