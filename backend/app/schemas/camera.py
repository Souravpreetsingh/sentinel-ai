"""Camera schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CameraStatus = Literal["online", "warning", "offline"]
CameraLifecycle = Literal["ACTIVE", "OFFLINE", "DEGRADED", "MAINTENANCE", "DISABLED"]
CameraProtocol = Literal["rtsp", "onvif", "vms", "hls", "webrtc"]


class CameraBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Display name of the camera")
    location: str = Field(..., min_length=1, max_length=256, description="Physical installation location")
    status: CameraStatus = Field("online")
    stream_url: str = Field("", max_length=512)
    resolution: str = Field("1080p", max_length=32)
    fps: int = Field(30, ge=1, le=240)
    ai_enabled: bool = Field(True)

    sector: str | None = Field(None, max_length=128)
    type: str | None = Field("visual", max_length=32)
    ai_capabilities: list[str] = Field(default_factory=list)
    health: float | None = Field(None, ge=0, le=100)
    bitrate: float | None = Field(None, ge=0)
    detections: dict[str, int] | None = None

    vendor: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=64)
    vms_source: str | None = Field(None, max_length=64)
    protocol: CameraProtocol | None = Field("rtsp")
    lifecycle_status: CameraLifecycle | None = None
    latitude: float | None = None
    longitude: float | None = None
    district: str | None = Field(None, max_length=64)
    zone: str | None = Field(None, max_length=64)
    road: str | None = Field(None, max_length=128)
    firmware: str | None = Field(None, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    error: str | None = Field(None, max_length=256)


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=128)
    location: str | None = Field(None, min_length=1, max_length=256)
    status: CameraStatus | None = None
    stream_url: str | None = Field(None, max_length=512)
    resolution: str | None = Field(None, max_length=32)
    fps: int | None = Field(None, ge=1, le=240)
    ai_enabled: bool | None = None
    sector: str | None = Field(None, max_length=128)
    type: str | None = Field(None, max_length=32)
    ai_capabilities: list[str] | None = None
    health: float | None = Field(None, ge=0, le=100)
    bitrate: float | None = Field(None, ge=0)
    detections: dict[str, int] | None = None

    vendor: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=64)
    vms_source: str | None = Field(None, max_length=64)
    protocol: CameraProtocol | None = None
    lifecycle_status: CameraLifecycle | None = None
    latitude: float | None = None
    longitude: float | None = None
    district: str | None = Field(None, max_length=64)
    zone: str | None = Field(None, max_length=64)
    road: str | None = Field(None, max_length=128)
    firmware: str | None = Field(None, max_length=64)
    capabilities: list[str] | None = None
    error: str | None = Field(None, max_length=256)


class CameraRead(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    last_seen: datetime | None = None
    last_heartbeat: datetime | None = None
    created_at: datetime
    updated_at: datetime
    lifecycle: str = "ACTIVE"