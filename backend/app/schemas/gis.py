"""GIS schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CameraLocation(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    status: str
    lifecycle: str = "ACTIVE"
    district: str | None = None
    zone: str | None = None
    road: str | None = None
    ai_enabled: bool = True
    last_seen: datetime | None = None
    detections: dict = Field(default_factory=dict)


class EventLocation(BaseModel):
    id: str
    kind: str = "alert"
    severity: str = "medium"
    status: str = "new"
    latitude: float
    longitude: float
    camera_id: str | None = None
    camera_name: str | None = None
    title: str
    timestamp: datetime
    confidence: float = 0.0


class RoutePoint(BaseModel):
    camera_id: str
    camera_name: str | None = None
    latitude: float
    longitude: float
    timestamp: datetime
    confidence: float = 0.0


class VehicleRouteRead(BaseModel):
    track_id: str
    entity_identifier: str | None = None
    watchlist_id: str | None = None
    status: str = "active"
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    points: list[RoutePoint] = Field(default_factory=list)


class GISSummary(BaseModel):
    camera_total: int
    camera_online: int
    camera_offline: int
    alert_total: int
    tracked_vehicles: int