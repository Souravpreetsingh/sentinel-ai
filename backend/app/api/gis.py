"""GIS API — camera/event layers, vehicle routes, summary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.errors import api_error
from app.schemas.gis import CameraLocation, EventLocation, GISSummary, VehicleRouteRead
from app.services import gis_service

router = APIRouter(prefix="/gis", tags=["gis"])

Db = Annotated[object, Depends(get_db)]


@router.get("/cameras", response_model=list[CameraLocation], summary="Camera GIS layer")
def camera_layer(db: Db):
    return gis_service.camera_locations(db)


@router.get("/events", response_model=list[EventLocation], summary="Recent alert locations")
def event_layer(db: Db, limit: int = 500):
    return gis_service.event_locations(db, limit=limit)


@router.get("/route/{entity_identifier}", response_model=VehicleRouteRead, summary="Vehicle route overlay")
def vehicle_route(db: Db, entity_identifier: str):
    """Chronological route for a tracked entity (matches on normalised plate)."""
    route = gis_service.vehicle_route(db, entity_identifier)
    if route is None:
        return VehicleRouteRead(
            track_id="", entity_identifier=entity_identifier, first_seen=None, last_seen=None,
            points=[], status="none",
        )
    return route


@router.get("/summary", response_model=GISSummary, summary="GIS / coverage summary")
def gis_summary(db: Db):
    return gis_service.summary(db)