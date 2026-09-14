"""Watchlist entity schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WatchlistCategory = Literal[
    "vehicle", "person",
    "stolen_vehicle", "wanted_person", "missing_person",
    "blacklisted_vehicle", "suspect_vehicle", "suspect_person", "other",
]
WatchlistPriority = Literal["critical", "high", "medium", "low"]
WatchlistStatus = Literal["active", "archived", "expired"]


class WatchlistBase(BaseModel):
    category: WatchlistCategory = Field(..., description="Entity classification")
    name: str = Field(..., min_length=1, max_length=256)
    priority: WatchlistPriority = Field("medium")
    vehicle_registration: str | None = Field(None, max_length=32)
    vehicle_type: str | None = Field(None, max_length=32)
    vehicle_make: str | None = Field(None, max_length=64)
    vehicle_model: str | None = Field(None, max_length=64)
    vehicle_colour: str | None = Field(None, max_length=32)
    person_age_range: str | None = Field(None, max_length=16)
    person_gender: str | None = Field(None, max_length=16)
    person_clothing: str | None = Field(None, max_length=256)
    person_remarks: str | None = None
    aliases: list[str] = Field(default_factory=list)
    reference_images: list[str] = Field(default_factory=list)
    notes: str | None = None


class WatchlistCreate(WatchlistBase):
    status: WatchlistStatus = Field("active")


class WatchlistUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: WatchlistCategory | None = None
    name: str | None = Field(None, min_length=1, max_length=256)
    priority: WatchlistPriority | None = None
    status: WatchlistStatus | None = None
    vehicle_registration: str | None = None
    vehicle_type: str | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_colour: str | None = None
    person_age_range: str | None = None
    person_gender: str | None = None
    person_clothing: str | None = None
    person_remarks: str | None = None
    aliases: list[str] | None = None
    reference_images: list[str] | None = None
    notes: str | None = None


class WatchlistRead(WatchlistBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: WatchlistStatus
    plate_normalized: str | None = None
    created_at: datetime
    updated_at: datetime