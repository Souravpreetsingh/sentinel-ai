"""WebSocket connection tests."""

import json

from fastapi.testclient import TestClient


def test_websocket_connects_and_receives_welcome(client: TestClient):
    with client.websocket_connect("/ws/live") as ws:
        raw = ws.receive_text()
        msg = json.loads(raw)
        assert msg["event"] == "system_status"
        assert msg["data"]["status"] == "connected"
        assert msg["data"]["service"] == "sentinel-ai"


def test_websocket_ping_pong(client: TestClient):
    with client.websocket_connect("/ws/live") as ws:
        # Drain the welcome message
        ws.receive_text()
        ws.send_text(json.dumps({"type": "ping", "data": "hello"}))
        raw = ws.receive_text()
        msg = json.loads(raw)
        assert msg["event"] == "pong"
        assert msg["data"]["echo"] == "hello"


def test_websocket_disconnect(client: TestClient):
    with client.websocket_connect("/ws/live") as ws:
        ws.receive_text()
        ws.close()
        # Should not raise
        assert True