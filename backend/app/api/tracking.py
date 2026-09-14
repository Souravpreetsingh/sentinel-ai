"""Vehicle tracking API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.schemas.track import MovementEventRead, TrackSummaryRead, VehicleTrackRead
from app.services import tracking_service

router = APIRouter(prefix="/tracking", tags=["tracking"])

Db = Annotated[object, Depends(get_db)]


def _track_ser(track, db) -> dict:
    data = {
        "id": track.id,
        "watchlist_id": track.watchlist_id,
        "entity_identifier": track.entity_identifier,
        "first_seen": track.first_seen,
        "last_seen": track.last_seen,
        "current_camera_id": track.current_camera_id,
        "current_latitude": track.current_latitude,
        "current_longitude": track.current_longitude,
        "hop_count": track.hop_count,
        "confidence": track.confidence,
        "status": track.status,
        "attributes": track.attributes,
        "movements": [],
    }
    names = tracking_service.camera_name_map(db)
    data["current_camera_name"] = names.get(track.current_camera_id) if track.current_camera_id else None
    moves = tracking_service.movements_for_track(db, track.id, limit=100)
    data["movements"] = [
        {
            "id": m.id,
            "camera_id": m.camera_id,
            "camera_name": names.get(m.camera_id) if m.camera_id else None,
            "detection_id": m.detection_id,
            "alert_id": m.alert_id,
            "evidence_id": m.evidence_id,
            "entity_identifier": m.entity_identifier,
            "latitude": m.latitude,
            "longitude": m.longitude,
            "speed_kmh": m.speed_kmh,
            "confidence": m.confidence,
            "metadata_json": m.metadata_json,
            "detected_at": m.detected_at,
        }
        for m in moves
    ]
    return data


@router.get("", response_model=list[TrackSummaryRead], summary="List vehicle tracks")
def list_tracks(
    db: Db,
    status: str | None = None,
    watchlist_id: str | None = None,
    entity_identifier: str | None = None,
    limit: int = 100,
):
    """List cross-camera tracks and their latest position."""
    tracks = tracking_service.list_tracks(db, status=status, watchlist_id=watchlist_id,
                                          entity_identifier=entity_identifier, limit=limit)
    names = tracking_service.camera_name_map(db)
    return [
        {
            "id": t.id,
            "entity_identifier": t.entity_identifier,
            "watchlist_id": t.watchlist_id,
            "first_seen": t.first_seen,
            "last_seen": t.last_seen,
            "current_camera_id": t.current_camera_id,
            "current_camera_name": names.get(t.current_camera_id) if t.current_camera_id else None,
            "hop_count": t.hop_count,
            "confidence": t.confidence,
            "status": t.status,
            "current_latitude": t.current_latitude,
            "current_longitude": t.current_longitude,
        }
        for t in tracks
    ]


@router.get("/{track_id}", response_model=VehicleTrackRead, summary="Get a track with movements")
def get_track(db: Db, track_id: str):
    track = tracking_service.get_track(db, track_id)
    return _track_ser(track, db)


@router.get("/entity/{entity_identifier}", response_model=list[MovementEventRead],
            summary="Movement history for an entity")
def entity_movements(db: Db, entity_identifier: str, limit: int = 500):
    moves = tracking_service.movements_for_entity(db, entity_identifier, limit=limit)
    names = tracking_service.camera_name_map(db)
    return [
        {
            "id": m.id,
            "camera_id": m.camera_id,
            "camera_name": names.get(m.camera_id) if m.camera_id else None,
            "detection_id": m.detection_id,
            "alert_id": m.alert_id,
            "evidence_id": m.evidence_id,
            "entity_identifier": m.entity_identifier,
            "latitude": m.latitude,
            "longitude": m.longitude,
            "speed_kmh": m.speed_kmh,
            "confidence": m.confidence,
            "metadata_json": m.metadata_json,
            "detected_at": m.detected_at,
        }
        for m in moves
    ]