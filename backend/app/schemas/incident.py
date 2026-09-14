"""Incident schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IncidentSeverity = Literal["critical", "high", "medium", "low"]
IncidentStatus = Literal["open", "investigating", "resolved"]


class IncidentBase(BaseModel):
    type: str = Field(..., min_length=1, max_length=128, description="Incident category, e.g. 'Restricted Zone Entry'")
    severity: IncidentSeverity
    camera_id: str | None = Field(None, max_length=32)
    location: str | None = Field(None, max_length=256)
    status: IncidentStatus = "open"
    detected_at: datetime | None = None
    duration: float | None = Field(None, ge=0, description="Duration in seconds")
    confidence: float = Field(0.0, ge=0, le=1)
    description: str | None = None
    assigned_to: str | None = Field(None, max_length=128)


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str | None = Field(None, min_length=1, max_length=128)
    severity: IncidentSeverity | None = None
    camera_id: str | None = Field(None, max_length=32)
    location: str | None = Field(None, max_length=256)
    status: IncidentStatus | None = None
    detected_at: datetime | None = None
    duration: float | None = Field(None, ge=0)
    confidence: float | None = Field(None, ge=0, le=1)
    description: str | None = None
    assigned_to: str | None = Field(None, max_length=128)


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    metadata_json: dict = Field(default_factory=dict, description="Open metadata attached to the incident")
    created_at: datetime
    updated_at: datetime