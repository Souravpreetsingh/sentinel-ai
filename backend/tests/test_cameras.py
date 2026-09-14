"""Camera API tests."""

from fastapi.testclient import TestClient


def test_list_seeded_cameras(client: TestClient):
    resp = client.get("/api/cameras")
    assert resp.status_code == 200
    cameras = resp.json()
    assert len(cameras) >= 8
    ids = {c["id"] for c in cameras}
    assert {"CAM-01", "CAM-02", "CAM-07"} <= ids
    cam = cameras[0]
    assert "name" in cam and "location" in cam and "status" in cam
    assert "stream_url" in cam and "ai_enabled" in cam and "resolution" in cam


def test_get_camera(client: TestClient):
    resp = client.get("/api/cameras/CAM-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "CAM-01"
    assert body["fps"] == 30


def test_get_camera_missing_returns_404(client: TestClient):
    resp = client.get("/api/cameras/CAM-NOPE")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_create_camera(client: TestClient):
    resp = client.post("/api/cameras", json={
        "name": "Test Dock Camera",
        "location": "Demo - Test Dock Platform",
        "status": "online",
        "resolution": "720p",
        "fps": 20,
        "ai_enabled": True,
        "stream_url": "rtsp://test.local/cam",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("CAM-")
    assert body["name"] == "Test Dock Camera"


def test_create_camera_validation(client: TestClient):
    resp = client.post("/api/cameras", json={"name": "", "location": ""})
    assert resp.status_code == 422


def test_patch_camera(client: TestClient):
    resp = client.patch("/api/cameras/CAM-01", json={"status": "warning", "ai_enabled": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "warning"
    assert body["ai_enabled"] is False


def test_delete_camera(client: TestClient):
    created = client.post("/api/cameras", json={
        "name": "Temp Camera", "location": "Demo - Temp",
    }).json()
    resp = client.delete(f"/api/cameras/{created['id']}")
    assert resp.status_code == 204
    resp = client.get(f"/api/cameras/{created['id']}")
    assert resp.status_code == 404