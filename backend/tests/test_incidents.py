"""Incident API tests."""

from fastapi.testclient import TestClient


def test_list_seeded_incidents(client: TestClient):
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    incidents = resp.json()
    assert len(incidents) >= 8
    severities = {i["severity"] for i in incidents}
    assert severities <= {"critical", "high", "medium", "low"}


def test_filter_by_severity(client: TestClient):
    resp = client.get("/api/incidents", params={"severity": "critical"})
    assert resp.status_code == 200
    assert all(i["severity"] == "critical" for i in resp.json())


def test_filter_by_status(client: TestClient):
    resp = client.get("/api/incidents", params={"status": "resolved"})
    assert resp.status_code == 200
    assert all(i["status"] == "resolved" for i in resp.json())


def test_get_incident(client: TestClient):
    resp = client.get("/api/incidents/INC-1042")
    assert resp.status_code == 200
    assert resp.json()["id"] == "INC-1042"


def test_get_missing_incident_404(client: TestClient):
    resp = client.get("/api/incidents/INC-XXXX")
    assert resp.status_code == 404


def test_create_incident(client: TestClient):
    resp = client.post("/api/incidents", json={
        "type": "Test Alert",
        "severity": "medium",
        "status": "open",
        "camera_id": "CAM-01",
        "location": "Demo - Test Zone",
        "confidence": 0.87,
        "description": "Automated test incident.",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("INC-")
    assert body["status"] == "open"


def test_create_incident_invalid_severity(client: TestClient):
    resp = client.post("/api/incidents", json={
        "type": "Bad", "severity": "urgent",
    })
    assert resp.status_code == 422


def test_patch_incident_status(client: TestClient):
    resp = client.patch("/api/incidents/INC-1042", json={"status": "resolved", "assigned_to": "Officer Test"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["assigned_to"] == "Officer Test"