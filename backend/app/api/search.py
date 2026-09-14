"""Unified investigation search API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.schemas.search import SearchResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])

Db = Annotated[object, Depends(get_db)]


@router.get("", response_model=SearchResponse, summary="Unified investigation search")
def search(
    db: Db,
    query: str = Query("", description="Free-text term (plate, name, camera, id)"),
    camera_id: str | None = None,
    district: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    tracking_id: str | None = None,
    watchlist_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 50,
):
    """Search across detections, alerts, tracks, watchlist, cameras and evidence."""
    return search_service.search(
        db, query,
        camera_id=camera_id, district=district, event_type=event_type, severity=severity,
        tracking_id=tracking_id, watchlist_id=watchlist_id, start=start, end=end, limit=limit,
    )


@router.get("/nearby", summary="Alerts near a location")
def nearby(
    db: Db,
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 20,
):
    """Return alerts within a radius of a lat/lon point."""
    return search_service.nearby_alerts(db, latitude, longitude, radius_km=radius_km, limit=limit)