"""Evidence service layer - file upload, hashing, storage.

Includes ``save_snapshot`` for capturing a BGR numpy frame as an incident
evidence file with SHA-256 provenance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2  # type: ignore
import numpy as np  # type: ignore
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import not_found, validation_error
from app.core.logging import get_logger
from app.models import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate
from app.services.hashing import sha256_file

logger = get_logger("services.evidence")


def next_evidence_id(db: Session) -> str:
    evds = db.query(Evidence.id).order_by(Evidence.id.desc()).limit(1).all()
    if not evds:
        return "EVD-2001"
    nums = []
    for (cid,) in evds:
        parts = cid.split("-", 1)
        if len(parts) == 2:
            try:
                nums.append(int(parts[1]))
            except ValueError:
                pass
    nxt = max(nums, default=0) + 1
    return f"EVD-{nxt}"


def list_evidence(
    db: Session,
    incident_id: str | None = None,
    camera_id: str | None = None,
    status: str | None = None,
) -> list[Evidence]:
    q = db.query(Evidence)
    if incident_id:
        q = q.filter(Evidence.incident_id == incident_id)
    if camera_id:
        q = q.filter(Evidence.camera_id == camera_id)
    if status:
        q = q.filter(Evidence.verification_status == status)
    return q.order_by(Evidence.created_at.desc()).all()


def get_evidence(db: Session, evidence_id: str) -> Evidence:
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if ev is None:
        raise not_found("Evidence", evidence_id)
    return ev


async def create_evidence(
    db: Session,
    file: UploadFile,
    meta: EvidenceCreate,
    settings: Settings | None = None,
) -> Evidence:
    settings = settings or get_settings()
    settings.ensure_dirs()

    if not file.filename:
        raise validation_error("Missing filename in upload.")

    ext = _extract_ext(file.filename)
    if ext not in settings.allowed_evidence_extensions_list:
        raise validation_error(
            f"File extension '.{ext}' is not allowed. "
            f"Allowed: {', '.join(settings.allowed_evidence_extensions_list)}"
        )

    file_id = uuid.uuid4().hex
    stored_name = f"{file_id}.{ext}"
    dest = settings.evidence_path() / stored_name

    total = 0
    too_large = False
    with open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 64)
            if not chunk:
                break
            total += len(chunk)
            if total > settings.max_upload_size_bytes:
                too_large = True
                break
            out.write(chunk)

    if too_large:
        dest.unlink(missing_ok=True)
        raise validation_error(f"File exceeds {settings.max_upload_size_mb} MB limit.")

    file_hash = sha256_file(dest)
    logger.info("Evidence uploaded: %s bytes, SHA-256=%s", total, file_hash[:16])

    ev = Evidence(
        id=next_evidence_id(db),
        incident_id=meta.incident_id,
        camera_id=meta.camera_id,
        type=meta.type,
        file_path=str(dest),
        file_size=total,
        hash=file_hash,
        verification_status=meta.verification_status or "pending",
        captured_at=meta.captured_at or datetime.now(timezone.utc),
        officer=meta.officer,
        title=meta.title or file.filename,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def update_evidence(db: Session, evidence_id: str, data: EvidenceUpdate) -> Evidence:
    ev = get_evidence(db, evidence_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(ev, field):
            setattr(ev, field, value)
    db.commit()
    db.refresh(ev)
    return ev


def _extract_ext(filename: str) -> str:
    from app.core.security import extract_extension
    return extract_extension(filename)


def save_snapshot(
    db: Session,
    frame: np.ndarray,
    incident_id: str | None = None,
    camera_id: str | None = None,
    title: str = "AI capture",
    settings: Settings | None = None,
) -> Evidence | None:
    """Persist a BGR frame as a JPEG evidence snapshot with SHA-256 hash.

    Returns the created ``Evidence`` row, or *None* when the frame is empty or
    a write error occurs. Errors are logged but never propagated — snapshots
    are best-effort.
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return None

    settings = settings or get_settings()
    settings.ensure_dirs()

    file_id = uuid.uuid4().hex
    stored_name = f"{file_id}.jpg"
    dest = settings.evidence_path() / stored_name

    try:
        success = cv2.imwrite(str(dest), frame)
        if not success:
            logger.warning("cv2.imwrite failed for snapshot %s", dest)
            return None
    except Exception:
        logger.exception("Snapshot write error")
        return None

    file_hash = sha256_file(dest)
    file_size = dest.stat().st_size

    ev = Evidence(
        id=next_evidence_id(db),
        incident_id=incident_id,
        camera_id=camera_id,
        type="snapshot",
        file_path=str(dest),
        file_size=file_size,
        hash=file_hash,
        verification_status="pending",
        captured_at=datetime.now(timezone.utc),
        title=title,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    logger.info("Snapshot saved: %s (%d bytes, SHA-256=%s)", dest.name, file_size, file_hash[:16])
    return ev