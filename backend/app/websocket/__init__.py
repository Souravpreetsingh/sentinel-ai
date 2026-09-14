"""WebSocket connection manager and real-time event broadcaster."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.logging import get_logger

logger = get_logger("websocket")


class ConnectionManager:
    """Manages connected WebSocket clients and broadcasts structured events."""

    def __init__(self) -> None:
        self._active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._active.add(websocket)
        logger.info("WebSocket connected (%d active)", len(self._active))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._active.discard(websocket)
        logger.info("WebSocket disconnected (%d active)", len(self._active))

    async def broadcast(self, event: str, data: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = {"event": event, "data": data, "timestamp": now}
        async with self._lock:
            clients = list(self._active)
        stale: list[WebSocket] = []
        for ws in clients:
            try:
                if ws.client_state != WebSocketState.CONNECTED:
                    stale.append(ws)
                    continue
                await ws.send_json(payload)
            except Exception:  # pragma: no cover
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    self._active.discard(ws)

    async def send_personal(self, websocket: WebSocket, event: str, data: Any) -> None:
        payload = {"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            await websocket.send_json(payload)
        except Exception:
            pass

    @property
    def active_count(self) -> int:
        return len(self._active)

    def broadcast_sync(self, event: str, data: Any) -> None:
        """Schedule a broadcast from synchronous code (e.g. worker threads)."""
        from app.core.runtime import runtime
        if runtime.loop is None or not runtime.loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(event, data), runtime.loop)
        except RuntimeError:
            pass