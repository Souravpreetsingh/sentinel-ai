"""Analytics API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.schemas.analytics import AnalyticsCameras, AnalyticsEvents, AnalyticsOverview, AnalyticsTraffic
from app.services import analytics_service

router = APIRouter(prefix="", tags=["analytics"])

Db = Annotated[object, Depends(get_db)]


@router.get("/overview", response_model=AnalyticsOverview, summary="Analytics overview")
def analytics_overview(db: Db):
    """Overall detection/incident statistics for the Analytics dashboard."""
    return analytics_service.overview(db)


@router.get("/events", response_model=AnalyticsEvents, summary="Event analytics")
def analytics_events(db: Db):
    """Event categories and hourly activity."""
    return analytics_service.events(db)


@router.get("/traffic", response_model=AnalyticsTraffic, summary="Traffic statistics")
def analytics_traffic(db: Db):
    """Pedestrian / vehicle traffic statistics."""
    return analytics_service.traffic(db)


@router.get("/cameras", response_model=AnalyticsCameras, summary="Camera utilization analytics")
def analytics_cameras(db: Db):
    """Camera utilization + status analytics."""
    return analytics_service.cameras(db)