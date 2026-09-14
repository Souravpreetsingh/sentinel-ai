"""Tracking / movement schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovementEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    camera_id: str | None = None
    camera_name: str | None = None
    detection_id: str | None = None
    alert_id: str | None = None
    evidence_id: str | None = None
    entity_identifier: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    confidence: float = 0.0
    metadata_json: dict = Field(default_factory=dict)
    detected_at: datetime


class VehicleTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    watchlist_id: str | None = None
    entity_identifier: str | None = None
    first_seen: datetime
    last_seen: datetime
    current_camera_id: str | None = None
    current_camera_name: str | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    hop_count: int = 0
    confidence: float = 0.0
    status: str = "active"
    attributes: dict = Field(default_factory=dict)
    movements: list[MovementEventRead] = Field(default_factory=list)


class TrackSummaryRead(BaseModel):
    id: str
    entity_identifier: str | None = None
    watchlist_id: str | None = None
    first_seen: datetime
    last_seen: datetime
    current_camera_id: str | None = None
    current_camera_name: str | None = None
    hop_count: int
    confidence: float
    status: str
    current_latitude: float | None = None
    current_longitude: float | None = None