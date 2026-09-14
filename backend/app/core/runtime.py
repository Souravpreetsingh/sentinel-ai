"""Process-wide runtime state: event loop + background executor.

Lets long-running (blocking) AI/video work run off the event loop while HTTP
and WebSocket handlers stay responsive.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.websocket.manager import ConnectionManager


class RuntimeState:
    def __init__(self) -> None:
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.executor: Optional[ThreadPoolExecutor] = None
        self.ws_manager: Optional[ConnectionManager] = None
        self.worker_thread_count: int = 4

    def init(self, loop: asyncio.AbstractEventLoop, worker_count: int = 4) -> None:
        self.loop = loop
        self.worker_thread_count = max(2, worker_count)
        self.executor = ThreadPoolExecutor(
            max_workers=self.worker_thread_count, thread_name_prefix="sentinel-worker"
        )

    def shutdown(self) -> None:
        if self.executor is not None:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = None
        self.loop = None


runtime = RuntimeState()


def broadcast_threadsafe(event: str, data: object) -> None:
    """Schedule a WebSocket broadcast from any (incl. worker) thread."""
    loop = runtime.loop
    manager = runtime.ws_manager
    if loop is None or manager is None or not loop.is_running():
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast(event, data), loop)