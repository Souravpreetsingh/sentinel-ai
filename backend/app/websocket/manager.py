"""Re-export the connection manager singleton."""

from app.websocket import ConnectionManager

manager = ConnectionManager()

__all__ = ["ConnectionManager", "manager"]