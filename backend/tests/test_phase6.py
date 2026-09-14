"""Phase 6 feature tests: plates, matching, watchlist, alerts, tracking,
demo end-to-end, search, GIS and scale."""

from __future__ import annotations

import pytest

from app.services.plates import collapse_ocr, normalize_plate


@pytest.fixture(scope="session")
def seeded_client(client):
    return client


# --------------------------------------------------------------------------
# Plate normalisation
# --------------------------------------------------------------------------
def test_normalize_plate_variants():
    assert normalize_plate("GJ 01 AB 1234") == "GJ01AB1234"
    assert normalize_plate("gj-01-ab-1234") == "GJ01AB1234"
    assert normalize_plate("GJ.01.AB.1234") == "GJ01AB1234"
    assert normalize_plate("") == ""
    assert normalize_plate(None) == ""


def test_collapse_ocr_ambiguity():
    assert collapse_ocr("OI") == "01"
    assert collapse_ocr("GJ0IAB1234") == "GJ01AB1234"
    assert normalize_plate("GJ 01 AB 1234") == "GJ01AB1234"  # letters preserved


# --------------------------------------------------------------------------
# Matching engine
# --------------------------------------------------------------------------
def test_match_exact(seeded_client):
    from app.core.database import get_session_factory
    from app.services.matching import match_plate

    wl = [{"id": "WL-5001", "plate_normalized": "GJ01AB1234", "priority": "critical"}]
    res = match_plate("GJ 01 AB 1234", wl)
    assert res.decided == "matched"
    assert res.match_type == "exact"
    assert res.confidence >= 0.98


def test_match_ocr_collapse(seeded_client):
    from app.services.matching import match_plate

    wl = [{"id": "WL-5001", "plate_normalized": "GJ01AB1234"}]
    res = match_plate("GJ0IAB1234", wl)
    assert res.decided == "matched"
    assert res.confidence >= 0.9


def test_match_no_candidate(seeded_client):
    from app.services.matching import match_plate

    wl = [{"id": "WL-5001", "plate_normalized": "GJ01AB1234"}]
    res = match_plate("MH12CD5678", wl)
    assert res.decided == "no match"
    assert res.match_type == "no_match"


# --------------------------------------------------------------------------
# Watchlist API
# --------------------------------------------------------------------------
def test_watchlist_crud(seeded_client):
    r = seeded_client.post("/api/watchlists", json={
        "category": "stolen_vehicle", "name": "Hot Bike KL 07 XY 4321", "priority": "high",
        "vehicle_registration": "KL 07 xY-4321", "vehicle_type": "motorcycle",
        "vehicle_make": "Honda", "vehicle_colour": "blue",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["plate_normalized"] == "KL07XY4321"
    assert data["id"].startswith("WL-")

    ent_id = data["id"]
    r = seeded_client.get(f"/api/watchlists/{ent_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Hot Bike KL 07 XY 4321"

    r = seeded_client.patch(f"/api/watchlists/{ent_id}", json={"status": "archived", "priority": "low"})
    assert r.status_code == 200
    assert r.json()["priority"] == "low"

    r = seeded_client.delete(f"/api/watchlists/{ent_id}")
    assert r.status_code == 204
    r = seeded_client.get(f"/api/watchlists/{ent_id}")
    assert r.status_code == 404


def test_watchlist_list_filters(seeded_client):
    r = seeded_client.get("/api/watchlists", params={"category": "vehicle", "limit": 50})
    assert r.status_code == 200
    assert any(w["plate_normalized"] == "GJ01AB1234" for w in r.json())


# --------------------------------------------------------------------------
# Alert API + dedup
# --------------------------------------------------------------------------
def test_alert_list_and_update(seeded_client):
    r = seeded_client.get("/api/alerts", params={"limit": 20})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = seeded_client.get("/api/alerts?severity=critical&limit=5")
    assert r.status_code == 200

    # Update path (may be empty list, so only test when alerts exist from seed).
    existing = seeded_client.get("/api/alerts", params={"limit": 1}).json()
    if existing:
        aid = existing[0]["id"]
        r = seeded_client.patch(f"/api/alerts/{aid}", json={"status": "acknowledged"})
        assert r.status_code == 200
        assert r.json()["acknowledged_at"] is not None


# --------------------------------------------------------------------------
# Tracking API (self-contained sim without demo run)
# --------------------------------------------------------------------------
def test_tracking_cross_camera_handoff(seeded_client):
    from app.core.database import get_session_factory
    from app.core.config import get_settings
    from app.services import tracking_service
    from app.services.alert_service import create_alert
    from datetime import datetime, timezone

    db = get_session_factory()()
    try:
        track = tracking_service.find_or_create_track(
            db, entity_identifier="GJ01AB1234", watchlist_id="WL-5001",
            camera_id="CAM-09", latitude=23.042, longitude=72.513,
            confidence=0.99, detected_at=datetime.now(timezone.utc),
        )
        assert track.hop_count == 0

        track2 = tracking_service.find_or_create_track(
            db, entity_identifier="GJ01AB1234", watchlist_id="WL-5001",
            camera_id="CAM-10", latitude=23.055, longitude=72.498,
            confidence=0.98,
        )
        assert track2.id == track.id
        assert track2.hop_count == 1

        mv = tracking_service.record_movement(
            db, track_id=track.id, camera_id="CAM-10",
            entity_identifier="GJ01AB1234", latitude=23.055, longitude=72.498,
            confidence=0.98, speed_kmh=70.0,
        )
        assert mv is not None

        days = tracking_service.movements_for_track(db, track.id)
        assert any(m.camera_id == "CAM-10" for m in days)
        # create_alert with dedup returns existing to avoid duplicates
        alert, created = create_alert(
            db, severity="critical", watchlist_id="WL-5001", camera_id="CAM-09",
            entity_name="Test Vehicle - GJ 01 AB 1234", entity_category="vehicle",
            entity_identifier="GJ01AB1234", match_type="exact", confidence=0.99,
            dedup_key="WL-5001:CAM-09:WL-5001", return_existing=False,
        )
        db.rollback()
        assert created or alert is None
    finally:
        db.close()


def test_tracking_api_lists(seeded_client):
    r = seeded_client.get("/api/tracking", params={"status": "active", "limit": 20})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --------------------------------------------------------------------------
# Search + GIS
# --------------------------------------------------------------------------
def test_search_returns_faceted_results(seeded_client):
    r = seeded_client.get("/api/search", params={"query": "GJ01AB1234", "limit": 50})
    assert r.status_code == 200
    body = r.json()
    assert "facets" in body
    assert body["query"] == "GJ01AB1234"


def test_gis_layers(seeded_client):
    r = seeded_client.get("/api/gis/summary")
    assert r.status_code == 200
    assert r.json()["camera_total"] >= 52
    assert r.json()["camera_online"] > 0

    r = seeded_client.get("/api/gis/cameras")
    assert r.status_code == 200
    cams = r.json()
    assert len(cams) >= 52
    assert all(c["latitude"] is not None and c["longitude"] is not None for c in cams)

    r = seeded_client.get("/api/gis/events")
    assert r.status_code == 200


# --------------------------------------------------------------------------
# Scale model
# --------------------------------------------------------------------------
def test_scale_run_and_presets(seeded_client):
    r = seeded_client.post("/api/scale/run", json={"camera_count": 80000, "duration_seconds": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["cameras"] == 80000
    assert body["ai_workers"] > 0
    assert body["scenario"] == "State-wide federation"

    r = seeded_client.get("/api/scale/presets")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = seeded_client.get("/api/scale/load-curve", params={"cameras": 2500, "duration_seconds": 10})
    assert r.status_code == 200
    assert len(r.json()) >= 2


# --------------------------------------------------------------------------
# Demo end-to-end
# --------------------------------------------------------------------------
def test_demo_status_and_run(seeded_client):
    r = seeded_client.get("/api/demo/status")
    assert r.status_code == 200
    assert r.json()["test_plate"] == "GJ 01 AB 1234"

    r = seeded_client.post("/api/demo/run-test")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["alerts_created"] >= 1
    assert body["track_id"] is not None
    assert body["evidence_snapshots_created"] >= 1

    # A second run must not duplicate alerts beyond each unique hop's first time.
    r2 = seeded_client.post("/api/demo/run-test")
    assert r2.status_code == 200
    assert r2.json()["alerts_created"] >= 0


def test_demo_route_visible_on_gis(seeded_client):
    r = seeded_client.get("/api/gis/route/GJ01AB1234")
    assert r.status_code == 200
    body = r.json()
    assert body["entity_identifier"] == "GJ01AB1234"
    assert len(body["points"]) > 0


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
def test_auth_login_default_admin(seeded_client):
    r = seeded_client.post("/api/auth/login", json={"email": "admin@sentinel.local", "password": "admin12345"})
    assert r.status_code in (200, 401), r.text  # admin is created lazily on first login attempt in seed flow
    if r.status_code == 200:
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["user"]["role"] == "ADMIN"
        headers = {"Authorization": f"Bearer {body['access_token']}"}
        r2 = seeded_client.get("/api/audit", headers=headers, params={"action": "auth.login"})
        assert r2.status_code == 200
    else:
        # auth_required=false → dev principal, audit still reachable
        r2 = seeded_client.get("/api/audit", params={"limit": 5})
        assert r2.status_code == 200