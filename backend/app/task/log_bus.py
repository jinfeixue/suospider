"""LogBus - real-time log distribution via WebSocket connections."""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set
from fastapi import WebSocket


class LogBus:
    """Manages WebSocket connections for real-time log streaming."""

    def __init__(self):
        # run_id -> set of WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._global_connections: Set[WebSocket] = set()
        self._db_func = None  # Will be set to save logs to DB

    def set_db_saver(self, func):
        """Set function to save logs to database."""
        self._db_func = func

    async def subscribe(self, run_id: int, ws: WebSocket):
        await ws.accept()
        if run_id not in self._connections:
            self._connections[run_id] = set()
        self._connections[run_id].add(ws)

    async def subscribe_global(self, ws: WebSocket):
        await ws.accept()
        self._global_connections.add(ws)

    def unsubscribe(self, run_id: int, ws: WebSocket):
        if run_id in self._connections:
            self._connections[run_id].discard(ws)
            if not self._connections[run_id]:
                del self._connections[run_id]

    def unsubscribe_global(self, ws: WebSocket):
        self._global_connections.discard(ws)

    async def push_log(self, run_id: int, level: str, message: str, timestamp: str = None):
        """Push a log message to all subscribers of a specific run."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        data = json.dumps({
            "type": "log",
            "run_id": run_id,
            "level": level,
            "message": message,
            "timestamp": timestamp,
        })
        # Send to run-specific subscribers
        targets = list(self._connections.get(run_id, set()))
        # Also send to global subscribers
        targets.extend(list(self._global_connections))
        dead = []
        for ws in targets:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            for rid, conns in self._connections.items():
                conns.discard(ws)
            self._global_connections.discard(ws)

        # Save to database
        if self._db_func:
            try:
                await self._db_func(run_id, level, message)
            except Exception:
                pass  # Don't let DB errors break log streaming

    async def push_status(self, run_id: int, status: str):
        """Push a status change event."""
        data = json.dumps({"type": "status", "run_id": run_id, "status": status})
        targets = list(self._connections.get(run_id, set()))
        targets.extend(list(self._global_connections))
        for ws in targets:
            try:
                await ws.send_text(data)
            except Exception:
                pass


# Singleton instance
log_bus = LogBus()


async def save_log_to_db(run_id: int, level: str, message: str):
    """Save log entry to database."""
    from app.core.database import get_sync_session
    try:
        from app.models import RunLog
        db = get_sync_session()
        try:
            log_entry = RunLog(run_id=run_id, level=level, message=message)
            db.add(log_entry)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


# Set the DB saver on module load
log_bus.set_db_saver(save_log_to_db)
