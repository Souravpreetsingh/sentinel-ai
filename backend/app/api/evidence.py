"""Evidence API endpoints - uploads are hashed and stored immutably."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.database import get_db
from app.core.errors import not_found
from app.core.config import get_settings
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceRead,
    EvidenceType,
    EvidenceUpdate,
    VerificationStatus,
)
from app.services import evidence_service

router = APIRouter(prefix="", tags=["evidence"])

Db = Annotated[object, Depends(get_db)]


@router.get("", response_model=list[EvidenceRead], summary="List evidence records")
def list_evidence(
    db: Db,
    incident_id: str | None = Query(None, description="Filter by incident id"),
    camera_id: str | None = Query(None, description="Filter by camera id"),
    status_filter: VerificationStatus | None = Query(None, alias="status", description="Filter by verification status"),
):
    """List evidence, optionally filtered by incident / camera / status."""
    return evidence_service.list_evidence(
        db,
        incident_id=incident_id,
        camera_id=camera_id,
        status=status_filter,
    )


@router.post(
    "",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload evidence",
)
async def create_evidence(
    db: Db,
    file: UploadFile = File(..., description="Evidence file to upload and hash"),
    type: EvidenceType = Form("video_clip"),
    incident_id: str | None = Form(None),
    camera_id: str | None = Form(None),
    officer: str | None = Form(None),
    title: str | None = Form(None),
    captured_at: datetime.datetime | None = Form(None),
    verification_status: VerificationStatus = Form("pending"),
):
    """Upload an evidence file.

    The file is stored under a server-generated name, its SHA-256 hash is
    computed, and the file is never modified afterwards.
    """
    meta = EvidenceCreate(
        type=type,
        incident_id=incident_id,
        camera_id=camera_id,
        officer=officer,
        title=title,
        captured_at=captured_at,
        verification_status=verification_status,
    )
    return await evidence_service.create_evidence(db, file, meta)


@router.get("/{evidence_id}/file", summary="Download an evidence file")
def evidence_file(db: Db, evidence_id: str):
    """Stream the stored file behind an evidence record (never modified).

    Paths are server-generated and absolute, so this is safe to expose for
    snapshot previews in the Evidence Vault UI.
    """
    ev = evidence_service.get_evidence(db, evidence_id)
    path = Path(ev.file_path)
    if not path.is_absolute():
        path = get_settings().evidence_path() / path.name
    if not path.is_file():
        raise not_found("Evidence file", evidence_id)
    return FileResponse(str(path), filename=path.name)


@router.get("/{evidence_id}", response_model=EvidenceRead, summary="Get evidence")
def get_evidence(db: Db, evidence_id: str):
    """Fetch an evidence record by id (e.g. EVD-2847)."""
    return evidence_service.get_evidence(db, evidence_id)


@router.patch("/{evidence_id}", response_model=EvidenceRead, summary="Update evidence metadata")
def update_evidence(db: Db, evidence_id: str, payload: EvidenceUpdate):
    """Update verification_status / officer / title. Never mutates the file."""
    return evidence_service.update_evidence(db, evidence_id, payload)