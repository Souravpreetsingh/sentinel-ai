"""Camera model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=False)

    status: Mapped[str] = mapped_column(String(24), default="online", nullable=False)
    stream_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    resolution: Mapped[str] = mapped_column(String(32), default="1080p", nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Phase 6 registry: heterogeneous CCTV provenance --------------------
    vendor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vms_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    protocol: Mapped[str | None] = mapped_column(
        String(16), default="rtsp", nullable=True
    )  # rtsp | onvif | vms | hls | webrtc
    lifecycle_status: Mapped[str] = mapped_column(
        String(16), default="ACTIVE", nullable=False, index=True
    )  # ACTIVE | OFFLINE | DEGRADED | MAINTENANCE | DISABLED

    # --- GIS ----------------------------------------------------------------
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    road: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # --- Health / heartbeat -------------------------------------------------
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    firmware: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # --- Frontend enrichment fields (optional, demo-friendly) ---
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    camera_type: Mapped[str] = mapped_column(String(32), default="visual", nullable=False)
    ai_capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    health: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    bitrate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detections: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    @property
    def type(self) -> str:
        return self.camera_type

    # Lifecycle mapping: legacy status values are normalised into the Phase 6
    # lifecycle vocabulary so both old and new consumers keep working.
    LIFECYCLE_FROM_STATUS: dict[str, str] = {
        "online": "ACTIVE",
        "active": "ACTIVE",
        "warning": "DEGRADED",
        "degraded": "DEGRADED",
        "offline": "OFFLINE",
        "maintenance": "MAINTENANCE",
        "disabled": "DISABLED",
    }

    STATUS_FROM_LIFECYCLE: dict[str, str] = {
        "ACTIVE": "online",
        "DEGRADED": "warning",
        "OFFLINE": "offline",
        "MAINTENANCE": "warning",
        "DISABLED": "offline",
    }

    @property
    def lifecycle(self) -> str:
        return self.LIFECYCLE_FROM_STATUS.get(self.status or "", "ACTIVE")