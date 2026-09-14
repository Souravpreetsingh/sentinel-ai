"""Video upload and analysis endpoint tests."""

import io

from fastapi.testclient import TestClient


def test_upload_video(client: TestClient):
    content = b"\x00mockvideo" * 100
    resp = client.post(
        "/api/video/upload",
        files={"file": ("test_video.mp4", io.BytesIO(content), "video/mp4")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["video_id"]
    assert body["filename"] == "test_video.mp4"
    assert body["status"] == "queued"


def test_upload_video_bad_extension(client: TestClient):
    resp = client.post(
        "/api/video/upload",
        files={"file": ("hack.exe", io.BytesIO(b"bad"), "application/octet-stream")},
    )
    assert resp.status_code == 422


def test_upload_video_oversized(client: TestClient):
    big = b"x" * (220 * 1024 * 1024)
    resp = client.post(
        "/api/video/upload",
        files={"file": ("big.mp4", io.BytesIO(big), "video/mp4")},
    )
    assert resp.status_code == 422


def test_video_status(client: TestClient):
    # Upload then check status.
    resp = client.post(
        "/api/video/upload",
        files={"file": ("vid.mp4", io.BytesIO(b"\x00" * 50), "video/mp4")},
    )
    vid = resp.json()["video_id"]
    resp = client.get(f"/api/video/{vid}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


def test_video_analyze(client: TestClient):
    resp = client.post(
        "/api/video/upload",
        files={"file": ("anal.mp4", io.BytesIO(b"\x00" * 100), "video/mp4")},
    )
    vid = resp.json()["video_id"]
    resp = client.post(f"/api/video/{vid}/analyze")
    assert resp.status_code == 200
    body = resp.json()
    assert body["video_id"] == vid


def test_video_status_missing_404(client: TestClient):
    resp = client.get("/api/video/nonexistent/status")
    assert resp.status_code == 404


def test_system_health(client: TestClient):
    resp = client.get("/api/system/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "ai_engine" in body
    assert "database" in body
    assert "gpu" in body
    assert "fps" in body
    assert "latency" in body
    assert "uptime" in body