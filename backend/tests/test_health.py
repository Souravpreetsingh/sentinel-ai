"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "sentinel-ai"
    assert body["version"] == "1.0.0"


def test_root(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "sentinel-ai"


def test_swagger_docs(client: TestClient):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_redoc(client: TestClient):
    resp = client.get("/redoc")
    assert resp.status_code == 200


def test_openapi(client: TestClient):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/cameras" in resp.json()["paths"]
    assert "/api/incidents" in resp.json()["paths"]
    assert "/api/evidence" in resp.json()["paths"]
    assert "/api/analytics/overview" in resp.json()["paths"]
    assert "/api/system/health" in resp.json()["paths"]