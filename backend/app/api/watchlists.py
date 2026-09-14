"""Watchlist entity API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.database import get_db
from app.schemas.watchlist import WatchlistCreate, WatchlistRead, WatchlistUpdate
from app.services import watchlist_service

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

Db = Annotated[object, Depends(get_db)]


@router.get("", response_model=list[WatchlistRead], summary="List watchlist entities")
def list_entities(
    db: Db,
    category: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    query: str | None = None,
    limit: int = 500,
):
    """List entities of interest with optional filters (category/status/priority/query)."""
    return watchlist_service.list_entities(db, category=category, status=status,
                                           priority=priority, query=query, limit=limit)


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED,
             summary="Add a watchlist entity")
def create_entity(db: Db, payload: WatchlistCreate):
    """Register a new person/vehicle of interest. Plates are normalised server-side."""
    return watchlist_service.create_entity(db, payload)


@router.get("/{entity_id}", response_model=WatchlistRead, summary="Get a watchlist entity")
def get_entity(db: Db, entity_id: str):
    return watchlist_service.get_entity(db, entity_id)


@router.patch("/{entity_id}", response_model=WatchlistRead, summary="Update a watchlist entity")
def update_entity(db: Db, entity_id: str, payload: WatchlistUpdate):
    return watchlist_service.update_entity(db, entity_id, payload)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a watchlist entity")
def delete_entity(db: Db, entity_id: str):
    watchlist_service.delete_entity(db, entity_id)