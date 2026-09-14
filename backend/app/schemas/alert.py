"""Alert schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AlertSeverity = Literal["critical", "high", "medium", "low"]
AlertStatus = Literal["new", "acknowledged", "investigating", "resolved", "false_positive"]
MatchType = Literal["exact", "fuzzy", "probable", "no_match"]


class AlertBase(BaseModel):
    severity: AlertSeverity = Field(..., description="Alert severity")
    watchlist_id: str | None = None
    camera_id: str | None = None
    entity_name: str
    entity_category: str
    entity_identifier: str | None = None
    match_type: MatchType = "no_match"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AlertStatus | None = None
    severity: AlertSeverity | None = None
    assigned_to: str | None = None
    notes: str | None = None


class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: AlertStatus
    detection_id: str | None = None
    tracking_id: str | None = None
    evidence_id: str | None = None
    snapshot_path: str | None = None
    detection_metadata: dict = Field(default_factory=dict)
    dedup_key: str | None = None
    detected_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime