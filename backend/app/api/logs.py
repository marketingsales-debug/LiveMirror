"""
In-memory log capture API for the LiveMirror dashboard.
Collects Python logging output and exposes it via REST + SSE.
"""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime
from typing import Deque, Dict, Any, List

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter()

_MAX_ENTRIES = 500


class _LogEntry:
    __slots__ = ("ts", "level", "logger", "message")

    def __init__(self, ts: str, level: str, logger: str, message: str):
        self.ts = ts
        self.level = level
        self.logger = logger
        self.message = message

    def to_dict(self) -> Dict[str, str]:
        return {
            "ts": self.ts,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
        }


_buffer: Deque[_LogEntry] = deque(maxlen=_MAX_ENTRIES)
_subscribers: List[asyncio.Queue] = []


class _DashboardHandler(logging.Handler):
    """Intercepts Python log records and pushes them to the in-memory ring buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        entry = _LogEntry(
            ts=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            logger=record.name,
            message=self.format(record),
        )
        _buffer.append(entry)
        dead: List[int] = []
        for i, q in enumerate(_subscribers):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                dead.append(i)
        for i in reversed(dead):
            _subscribers.pop(i)


def install_log_handler() -> None:
    """Attach the dashboard handler to the root logger."""
    handler = _DashboardHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    # Force INFO level so dashboard gets logs
    root.setLevel(logging.INFO)


@router.get("")
async def get_logs(
    limit: int = Query(default=100, ge=1, le=500),
    level: str = Query(default=""),
) -> Dict[str, Any]:
    """Return the most recent log entries from the ring buffer."""
    entries = list(_buffer)
    if level:
        upper = level.upper()
        entries = [e for e in entries if e.level == upper]
    entries = entries[-limit:]
    return {"logs": [e.to_dict() for e in entries], "total": len(_buffer)}


@router.get("/stream")
async def stream_logs() -> StreamingResponse:
    """SSE endpoint that pushes new log entries in real time."""
    queue: asyncio.Queue[_LogEntry] = asyncio.Queue(maxsize=200)
    _subscribers.append(queue)

    async def _generate():
        try:
            while True:
                entry = await queue.get()
                data = json.dumps(entry.to_dict())
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
