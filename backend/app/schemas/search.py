"""Unified search schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    kind: str  # detection | alert | track | watchlist | camera | evidence
    id: str
    title: str
    subtitle: str | None = None
    timestamp: datetime | None = None
    camera_id: str | None = None
    camera_name: str | None = None
    severity: str | None = None
    status: str | None = None
    confidence: float | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    extra: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultItem] = Field(default_factory=list)
    facets: dict = Field(
        default_factory=lambda: {
            "detections": 0,
            "alerts": 0,
            "tracks": 0,
            "watchlist": 0,
            "cameras": 0,
            "evidence": 0,
        }
    )