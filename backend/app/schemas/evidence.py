"""Evidence schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceType = Literal["video_clip", "snapshot", "audio", "sensor_log", "document", "other"]
VerificationStatus = Literal["verified", "pending", "flagged"]


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EvidenceType
    incident_id: str | None = Field(None, max_length=32)
    camera_id: str | None = Field(None, max_length=32)
    captured_at: datetime | None = None
    officer: str | None = Field(None, max_length=128)
    title: str | None = Field(None, max_length=256)
    verification_status: VerificationStatus = "pending"


class EvidenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_status: VerificationStatus | None = None
    officer: str | None = Field(None, max_length=128)
    title: str | None = Field(None, max_length=256)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str | None
    camera_id: str | None
    type: EvidenceType
    file_size: int
    hash: str
    verification_status: VerificationStatus
    captured_at: datetime
    officer: str | None
    title: str | None
    created_at: datetime