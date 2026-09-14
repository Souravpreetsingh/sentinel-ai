"""Evidence API + SHA-256 hashing tests."""

import hashlib
import io

from fastapi.testclient import TestClient

from app.services.hashing import sha256_bytes, sha256_file


def test_sha256_bytes():
    assert sha256_bytes(b"sentinel") == hashlib.sha256(b"sentinel").hexdigest()


def test_sha256_file(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_bytes(b"evidence-content-123")
    assert sha256_file(target) == hashlib.sha256(b"evidence-content-123").hexdigest()


def test_upload_evidence_hash_matches_file(client: TestClient, tmp_path):
    content = b"\x00\x01badpixelvideo\xff" * 4096
    resp = client.post(
        "/api/evidence",
        data={"type": "video_clip", "title": "Test Clip", "officer": "Officer Test"},
        files={"file": ("clip_sample.mp4", io.BytesIO(content), "video/mp4")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["verification_status"] == "pending"
    assert body["file_size"] == len(content)
    assert body["hash"] == hashlib.sha256(content).hexdigest()
    evidence_id = body["id"]

    stored = client.get(f"/api/evidence/{evidence_id}").json()
    assert stored["hash"] == body["hash"]

    # File served via GET /evidence/{id}/file must be unchanged after hashing.
    downloaded = client.get(f"/api/evidence/{evidence_id}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert hashlib.sha256(downloaded.content).hexdigest() == body["hash"]


def test_upload_evidence_rejects_bad_extension(client: TestClient):
    resp = client.post(
        "/api/evidence",
        data={"type": "document"},
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert resp.status_code == 422


def test_upload_evidence_rejects_oversize(client: TestClient):
    big = b"x" * (210 * 1024 * 1024)
    resp = client.post(
        "/api/evidence",
        data={"type": "video_clip"},
        files={"file": ("huge.mp4", io.BytesIO(big), "video/mp4")},
    )
    assert resp.status_code == 422


def test_patch_evidence_status(client: TestClient):
    content = b"patch-me"
    created = client.post(
        "/api/evidence",
        data={"type": "snapshot", "title": "Snapshot"},
        files={"file": ("snap.png", io.BytesIO(content), "image/png")},
    ).json()
    resp = client.patch(
        f"/api/evidence/{created['id']}",
        json={"verification_status": "verified"},
    )
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "verified"


def test_list_evidence_filter(client: TestClient):
    resp = client.get("/api/evidence", params={"status": "verified"})
    assert resp.status_code == 200
    assert all(e["verification_status"] == "verified" for e in resp.json())