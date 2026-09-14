"""Pydantic schemas."""

from app.schemas.analytics import (
    AnalyticsCameras,
    AnalyticsEvents,
    AnalyticsOverview,
    AnalyticsTraffic,
)
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.schemas.common import ApiError, ApiMessage
from app.schemas.evidence import EvidenceCreate, EvidenceRead, EvidenceUpdate
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate
from app.schemas.system import SystemHealth
from app.schemas.video import (
    VideoAnalyzeResponse,
    VideoStatusResponse,
    VideoUploadResponse,
)

__all__ = [
    "AnalyticsCameras",
    "AnalyticsEvents",
    "AnalyticsOverview",
    "AnalyticsTraffic",
    "ApiError",
    "ApiMessage",
    "CameraCreate",
    "CameraRead",
    "CameraUpdate",
    "EvidenceCreate",
    "EvidenceRead",
    "EvidenceUpdate",
    "IncidentCreate",
    "IncidentRead",
    "IncidentUpdate",
    "SystemHealth",
    "VideoAnalyzeResponse",
    "VideoStatusResponse",
    "VideoUploadResponse",
]