"""Demo simulator — end-to-end Phase 6 showcase for the designated test vehicle.

Walking the Gujarat corridor (CAM-09 … CAM-14) with plate ``GJ 01 AB 1234``
exercises the whole Phase 6 pipeline in one run:

    detection → ANPR read → watchlist matching → alert (dedup) → cross-camera
    tracking → movement events → evidence snapshots → GIS route → WS events

Every hop deliberately uses a slightly different plate spelling so visitors can
see fuzzy/OCR matching work, while the confidence stays above the critical
threshold so the alert fires.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Camera, Detection, Evidence, WatchlistEntity
from app.services.alert_service import create_alert, recent_deduped
from app.services.matching import match_plate
from app.services.plates import normalize_plate
from app.services.seed import DEMO_ROUTE_CAMERA_IDS, DEMO_TEST_PLATE
from app.services.tracking_service import (
    find_or_create_track,
    record_movement,
)

logger = get_logger("services.demo")

_DEMO_JPEG = (
    b"/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBk"
    b"SEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAB"
    b"AAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAA"
    b"AAD/2gAIAQEAAD8AVN//2Q=="
)

# Slightly misspelled variants the "ANPR" reports for this plate, one per hop.
_OCR_VARIANTS = [DEMO_TEST_PLATE, "GJ-01 AB 1234", "GJ0I AB 1234", "GJ 01 A9 1234", "GJ01AB1234", "GJ 0L AB 1234"]


def _broadcast(event: str, data: dict) -> None:
    """Broadcast a WS event from synchronous service code."""
    from app.websocket.manager import manager
    from app.core.runtime import runtime

    if runtime.loop is None or not runtime.loop.is_running():
        return
    import asyncio
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(event, data), runtime.loop)
    except RuntimeError:
        pass


def run_demo_test(db: Session) -> dict:
    """Simulate the test vehicle driving the Gujarat corridor once."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # Entity of interest: the seeded watchlist entry for the demo plate.
    entity = db.query(WatchlistEntity).filter(WatchlistEntity.id == "WL-5001").first()
    if entity is None:
        from app.schemas.watchlist import WatchlistCreate
        from app.services.watchlist_service import create_entity
        entity = create_entity(db, WatchlistCreate(
            category="vehicle", name="Test Vehicle - GJ 01 AB 1234", priority="critical",
            vehicle_registration=DEMO_TEST_PLATE, vehicle_type="sedan", vehicle_make="Toyota",
            vehicle_model="Camry", vehicle_colour="silver",
        ))

    cameras = {c.id: c for c in db.query(Camera).filter(Camera.id.in_(DEMO_ROUTE_CAMERA_IDS)).all()}
    if any(cid not in cameras for cid in DEMO_ROUTE_CAMERA_IDS):
        missing = [cid for cid in DEMO_ROUTE_CAMERA_IDS if cid not in cameras]
        raise RuntimeError(f"Demo corridor cameras missing from registry: {missing}")

    watchlist_rows = [
        {
            "id": e.id,
            "category": e.category,
            "priority": e.priority,
            "plate_normalized": e.plate_normalized or "",
            "name": e.name,
        }
        for e in db.query(WatchlistEntity).all()
        if e.category == "vehicle" and e.plate_normalized
    ]

    outcomes = []
    alerts_created = 0
    events_created = 0
    evidence_created = 0
    track = None
    first_detection_ts = None

    settings_objs = get_settings()

    # The demo vehicle's canonical identity is its watchlist registration.
    # OCR reads vary per hop (GJ0IAB1234, GJ01A91234, GJ 0L AB 1234 ...) but
    # the matched entity is always the same designated vehicle, so every hop
    # stores the SAME entity_identifier -> a complete cross-camera trail.
    canonical_entity = normalize_plate(DEMO_TEST_PLATE) or "GJ01AB1234"

    for idx, cid in enumerate(DEMO_ROUTE_CAMERA_IDS):
        cam = cameras[cid]
        hop_ts = now + timedelta(seconds=idx * 90)  # ~90 s between hops
        if first_detection_ts is None:
            first_detection_ts = hop_ts

        variant = _OCR_VARIANTS[idx % len(_OCR_VARIANTS)]
        confidence = round(random.uniform(0.84, 0.97), 4)
        track_label = f"V#{1000 + idx}"

        # 1) Detection row.
        det = Detection(
            id=f"DET-{uuid.uuid4().hex[:10].upper()}",
            camera_id=cid,
            class_name="vehicle",
            confidence=confidence,
            x1=120.0, y1=60.0, x2=420.0, y2=300.0,
            track_id=track_label,
            source="demo",
            detected_at=hop_ts,
        )
        db.add(det)
        db.flush()

        # 2) Watchlist matching against the ANPR spelling variant.
        match_result = match_plate(variant, watchlist_rows, settings_objs)
        logger.info(
            "demo detect camera=%s read=%r normalized=%r confidence=%.4f decided=%s type=%s",
            cid, variant, match_result.normalized_plate, match_result.confidence,
            match_result.decided, match_result.match_type,
        )

        # 3) Alert (dedup on entity + camera + watchlist).
        dedup_key = f"{entity.id}:{cid}:{match_result.watchlist_id or ''}" if match_result.decided != "no match" else None
        severity = "critical" if match_result.decided == "matched" else ("high" if match_result.decided == "probable match" else "low")

        already_alarmed = dedup_key is not None and recent_deduped(
            db, dedup_key, settings_objs.alert_cooldown_seconds
        ) is not None
        is_new_match = match_result.decided != "no match" and not already_alarmed

        evidence_id = None
        evidence_path = None
        if is_new_match:
            evidence_id, evidence_path = _write_demo_snapshot(db, cid, idx)
            evidence_created += 1
            logger.info("demo evidence evidence_id=%s camera=%s path=%s", evidence_id, cid, evidence_path)

        alert, created = create_alert(
            db,
            severity=severity,
            watchlist_id=match_result.watchlist_id,
            camera_id=cid,
            entity_name=match_result.candidate["name"] if match_result.decided != "no match" else f"Vehicle {variant}",
            entity_category="vehicle",
            entity_identifier=canonical_entity,
            match_type=match_result.match_type,
            confidence=match_result.confidence,
            location=cam.location,
            latitude=cam.latitude,
            longitude=cam.longitude,
            detection_id=det.id,
            evidence_id=evidence_id,
            snapshot_path=evidence_path,
            detection_metadata={
                "read_plate": variant,
                "normalized_plate": match_result.normalized_plate,
                "scrutineering": match_result.scrutineering,
                "camera": cam.name,
                "hop_index": idx,
            },
            dedup_key=dedup_key,
            detected_at=hop_ts,
            return_existing=True,
        )
        if created and alert is not None:
            alerts_created += 1
            logger.info(
                "demo alert alert_id=%s severity=%s watchlist=%s camera=%s match_type=%s confidence=%.4f",
                alert.id, alert.severity, alert.watchlist_id, cid,
                alert.match_type, alert.confidence,
            )
        else:
            logger.info("demo alert duplicate alert_id=%s camera=%s (idempotent re-run)", alert.id if alert else None, cid)

        # 4) Cross-camera tracking (new alerts only — re-runs stay idempotent).
        if created and alert is not None and alert.watchlist_id:
            track = find_or_create_track(
                db,
                entity_identifier=canonical_entity,
                watchlist_id=alert.watchlist_id,
                camera_id=cid,
                latitude=cam.latitude,
                longitude=cam.longitude,
                confidence=alert.confidence,
                detected_at=hop_ts,
                attributes={
                    "make": entity.vehicle_make or "",
                    "model": entity.vehicle_model or "",
                    "colour": entity.vehicle_colour or "",
                    "type": entity.vehicle_type or "",
                },
            )
            move = record_movement(
                db,
                track_id=track.id,
                camera_id=cid,
                entity_identifier=canonical_entity,
                latitude=cam.latitude,
                longitude=cam.longitude,
                confidence=alert.confidence,
                detected_at=hop_ts,
                detection_id=det.id,
                alert_id=alert.id,
                evidence_id=evidence_id,
                speed_kmh=round(random.uniform(34.0, 78.0), 1),
                metadata_json={"read_plate": variant},
            )
            if move:
                events_created += 1
            logger.info(
                "demo tracking track_id=%s camera=%s movement=%s handoff=%s",
                track.id, cid, move.id if move else None,
                "yes" if move else "first-hop",
            )

        # 5) Realtime WS events for the live dashboard.
        _broadcast("detection", {
            "camera_id": cid,
            "timestamp": hop_ts.isoformat(),
            "objects": [{
                "class_name": "vehicle",
                "track_id": track_label,
                "confidence": confidence,
                "bbox": [120, 60, 420, 300],
            }],
        })
        if created and alert is not None:
            _broadcast("alert.created", {
                "id": alert.id,
                "severity": alert.severity,
                "status": alert.status,
                "watchlist_id": alert.watchlist_id,
                "camera_id": alert.camera_id,
                "entity_name": alert.entity_name,
                "match_type": alert.match_type,
                "confidence": alert.confidence,
            })

        outcomes.append({
            "camera_id": cid,
            "camera_name": cam.name,
            "plate_read": variant,
            "normalized": normalize_plate(variant),
            "match": match_result.decided,
            "match_type": match_result.match_type,
            "confidence": match_result.confidence,
            "alert_id": alert.id if alert else None,
            "alert_created": created,
        })

    db.commit()

    return {
        "status": "completed",
        "test_plate": DEMO_TEST_PLATE,
        "normalized": normalize_plate(DEMO_TEST_PLATE),
        "route": DEMO_ROUTE_CAMERA_IDS,
        "hops": len(DEMO_ROUTE_CAMERA_IDS),
        "detections_created": len(DEMO_ROUTE_CAMERA_IDS),
        "alerts_created": alerts_created,
        "movement_events_created": events_created,
        "evidence_snapshots_created": evidence_created,
        "track_id": track.id if track else None,
        "first_seen": first_detection_ts.isoformat(),
        "last_seen": (first_detection_ts + timedelta(seconds=(len(DEMO_ROUTE_CAMERA_IDS) - 1) * 90)).isoformat(),
        "log": outcomes,
    }


def _write_demo_snapshot(db: Session, camera_id: str, index: int) -> tuple[str, str]:
    """Persist a tiny demo JPEG to the evidence dir and return (evidence_id, path)."""
    settings = get_settings()
    evidence_dir = settings.evidence_path()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    name = f"demo_snapshot_{camera_id}_{index}.jpg"
    dest: Path = evidence_dir / name
    dest.write_bytes(_DEMO_JPEG)

    import hashlib
    digest = f"SHA256: {hashlib.sha256(dest.read_bytes()).hexdigest()}"

    ev = Evidence(
        id=f"EVD-{uuid.uuid4().hex[:8].upper()}",
        camera_id=camera_id,
        type="snapshot",
        file_path=str(dest),
        file_size=dest.stat().st_size,
        hash=digest,
        verification_status="pending",
        captured_at=datetime.now(timezone.utc),
        title=f"Demo ANPR snapshot CAM {camera_id}",
    )
    db.add(ev)
    db.flush()
    return ev.id, str(dest)


def demo_status(db: Session) -> dict:
    """Current demo configuration + whether a recent run exists."""
    from app.models import Alert, MovementEvent, VehicleTrack

    alert_count = db.query(Alert).count() or 0
    track_count = db.query(VehicleTrack).count() or 0
    move_count = db.query(MovementEvent).count() or 0
    entity = db.query(WatchlistEntity).filter(WatchlistEntity.id == "WL-5001").first()
    return {
        "test_plate": DEMO_TEST_PLATE,
        "normalized": normalize_plate(DEMO_TEST_PLATE),
        "route": DEMO_ROUTE_CAMERA_IDS,
        "watchlist_ready": entity is not None,
        "alerts_total": alert_count,
        "tracks_total": track_count,
        "movement_events_total": move_count,
        "description": "POST /api/system/demo/run-test simulates the test vehicle driving the Gujarat corridor (CAM-09..CAM-14), producing detections, match alerts, a cross-camera track and evidence snapshots.",
    }


def reset_demo(db: Session) -> dict:
    """Reset Phase 6 demo data to a clean, re-runnable state.

    Removes every dynamic artifact a previous demo run created (movements,
    tracks, alerts, demo detections, demo evidence + snapshot files), then
    re-verifies the demo prerequisites (52 cameras + the ``GJ 01 AB 1234``
    watchlist entry) so ``run_demo_test`` can start a clean run.
    """
    from app.models import Alert, Detection, Evidence, MovementEvent, VehicleTrack

    movements = db.query(MovementEvent).delete()
    alerts = db.query(Alert).delete()
    evidence_rows = db.query(Evidence).filter(Evidence.title.like("Demo ANPR snapshot%")).all()
    evidence_cleared = len(evidence_rows)
    files_removed = 0
    for ev in evidence_rows:
        if ev.file_path:
            try:
                dest = Path(ev.file_path)
                if dest.exists():
                    dest.unlink()
                    files_removed += 1
            except OSError:
                pass
        db.delete(ev)
    tracks = db.query(VehicleTrack).delete()
    detections = db.query(Detection).filter(Detection.source == "demo").delete(synchronize_session=False)
    db.commit()

    from app.services.seed import seed_if_empty
    seed_if_empty(db)
    camera_ids = {cid for (cid,) in db.query(Camera.id).all()}
    entity = db.query(WatchlistEntity).filter(WatchlistEntity.id == "WL-5001").first()

    readiness = {
        "cameras": len(camera_ids),
        "route_cameras_ready": all(cid in camera_ids for cid in DEMO_ROUTE_CAMERA_IDS),
        "watchlist_ready": entity is not None,
    }
    logger.info(
        "demo reset complete: alerts=%d tracks=%d movements=%d detections=%d evidence=%d files=%d readiness=%s",
        alerts, tracks, movements, detections, evidence_cleared, files_removed, readiness,
    )
    return {
        "status": "reset",
        "cleared": {
            "alerts": alerts,
            "tracks": tracks,
            "movements": movements,
            "detections": detections,
            "evidence": evidence_cleared,
        },
        "files_removed": files_removed,
        "readiness": readiness,
    }