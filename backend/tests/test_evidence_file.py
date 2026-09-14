"""Tests for evidence file retrieval endpoint and response sanitization."""

import io
from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient) -> dict:
    resp = client.post(
        "/api/evidence",
        data={"type": "video_clip", "title": "Evidence file test"},
        files={"file": ("test_clip.mp4", io.BytesIO(b"\x00MP4fake" * 1024), "video/mp4")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_evidence_file_download_ok(client: TestClient):
    body = _upload(client)
    evidence_id = body["id"]
    resp = client.get(f"/api/evidence/{evidence_id}/file")
    assert resp.status_code == 200
    assert "video/mp4" in resp.headers.get("content-type", "")
    assert len(resp.content) == body["file_size"]


def test_evidence_file_not_found(client: TestClient):
    resp = client.get("/api/evidence/EVD-99999/file")
    assert resp.status_code == 404
    detail = resp.json().get("detail", {})
    assert isinstance(detail, dict)
    assert "Evidence" in f'{detail.get("code", "")} {detail.get("message", "")}'


def test_evidence_file_malformed_id(client: TestClient):
    resp = client.get("/api/evidence/!!!/file")
    assert resp.status_code == 404
    assert resp.headers.get("content-type", "").startswith("application/json")


def test_evidence_file_missing_on_disk(client: TestClient):
    body = _upload(client)
    evidence_id = body["id"]

    from app.core.database import get_session_factory
    from app.models import Evidence

    with get_session_factory()() as db:
        ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        assert ev is not None
        target = Path(ev.file_path)

    assert target.is_file(), "uploaded evidence file should exist on disk"
    target.unlink()

    resp = client.get(f"/api/evidence/{evidence_id}/file")
    assert resp.status_code == 404


def test_evidence_response_has_no_file_path(client: TestClient):
    body = _upload(client)
    assert "file_path" not in body
    # Single-record endpoint should also omit file_path.
    resp = client.get(f"/api/evidence/{body['id']}")
    assert resp.status_code == 200
    assert "file_path" not in resp.json()
    # Response should never contain absolute filesystem paths.
    import json
    full = json.dumps(resp.json())
    assert ":\\" not in full
    assert "/uploads/" not in full


def test_evidence_list_has_no_file_path(client: TestClient):
    _upload(client)
    resp = client.get("/api/evidence")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    for item in items:
        assert "file_path" not in item
