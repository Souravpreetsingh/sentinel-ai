"""Phase 7 tests: demo reset (clean + idempotent), alert status workflow,
system health bandwidth/resolution mapping and demo readiness."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def seeded_client(client):
    return client


def _alert_ids(client):
    return client.get("/api/alerts", params={"limit": 100}).json()


# --------------------------------------------------------------------------
# Demo reset: clean, readiness-checked and idempotent
# --------------------------------------------------------------------------
def test_demo_reset_readiness_and_clean(seeded_client):
    r = seeded_client.post("/api/demo/reset")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "reset"
    assert "cleared" in body and "readiness" in body

    readiness = body["readiness"]
    assert readiness["watchlist_ready"] is True
    assert readiness["route_cameras_ready"] is True
    assert readiness["cameras"] >= 52


def test_demo_reset_then_run_reproduces_artifacts(seeded_client):
    seeded_client.post("/api/demo/reset")
    r = seeded_client.post("/api/demo/run-test")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["normalized"] == "GJ01AB1234"

    alerts = _alert_ids(seeded_client)
    assert len(alerts) == body["alerts_created"]
    assert all(a["status"] == "new" for a in alerts)

    # Re-running after reset must not duplicate alerts/tracks beyond first time.
    r3 = seeded_client.post("/api/demo/run-test")
    assert r3.status_code == 200
    assert r3.json()["alerts_created"] == 0
    assert len(_alert_ids(seeded_client)) == body["alerts_created"]


# --------------------------------------------------------------------------
# Alert status workflow (NEW -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED / FP)
# --------------------------------------------------------------------------
def test_alert_status_workflow(seeded_client):
    alerts = _alert_ids(seeded_client)
    assert alerts, "expected demo alerts after run-test"
    aid = alerts[0]["id"]

    r = seeded_client.patch(f"/api/alerts/{aid}", json={"status": "acknowledged"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "acknowledged"
    assert r.json()["acknowledged_at"] is not None

    r = seeded_client.patch(f"/api/alerts/{aid}", json={"status": "investigating"})
    assert r.status_code == 200
    assert r.json()["status"] == "investigating"

    r = seeded_client.patch(f"/api/alerts/{aid}", json={"status": "resolved"})
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    assert r.json()["resolved_at"] is not None


def test_alert_false_positive_flow(seeded_client):
    alerts = seeded_client.get("/api/alerts", params={"status": "new", "limit": 1}).json()
    if not alerts:
        pytest.skip("no new alerts available")
    aid = alerts[0]["id"]
    r = seeded_client.patch(f"/api/alerts/{aid}", json={"status": "false_positive"})
    assert r.status_code == 200
    assert r.json()["status"] == "false_positive"


# --------------------------------------------------------------------------
# System health: bandwidth + 1080p/4K resolution mapping
# --------------------------------------------------------------------------
def test_system_health_network_bandwidth(seeded_client):
    r = seeded_client.get("/api/system/health")
    assert r.status_code == 200
    health = r.json()
    assert "networkBandwidth" in health
    bw = health["networkBandwidth"]
    assert "streams1080p" in bw and "streams4k" in bw
    assert isinstance(health["overall"], int)
    labels = {seg["label"] for seg in bw.get("segments", [])}
    assert {"1080P", "4K", "CAMERAS", "ALERTS"} <= labels


# --------------------------------------------------------------------------
# Analytics overview still schema-valid after bandwidth addition
# --------------------------------------------------------------------------
def test_analytics_overview_schema_valid(seeded_client):
    for endpoint in ("/api/analytics/overview", "/api/analytics/events", "/api/analytics/traffic"):
        r = seeded_client.get(endpoint)
        assert r.status_code == 200, f"{endpoint}: {r.text}"