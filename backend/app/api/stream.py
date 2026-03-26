"""
Server-Sent Events (SSE) endpoint for real-time frontend updates.
Owner: Claude

Streams live data to the dashboard:
- Ingestion progress (signals found per platform)
- Simulation state (agent actions, round progress)
- Prediction updates (new predictions, validation results)
- System health changes
"""

import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


class EventBus:
    """
    Simple in-memory event bus for SSE.
    Components push events, SSE endpoint streams them to frontend.
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Create a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        # Clean up overflowed queues
        for q in dead_queues:
            self._subscribers.remove(q)


# Global event bus — components import this to publish events
event_bus = EventBus()


async def _event_generator(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Generate SSE-formatted events from a queue."""
    try:
        # Send initial connection confirmation
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                event_type = message.get("type", "update")
                data = json.dumps(message, default=str)
                yield f"event: {event_type}\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.now().isoformat()})}\n\n"
    except asyncio.CancelledError:
        pass


@router.get("/events")
async def stream_events():
    """
    SSE endpoint — streams real-time events to the frontend.

    Event types:
    - connected: initial connection confirmation
    - heartbeat: keep-alive (every 30s)
    - ingestion_progress: signals found per platform
    - ingestion_complete: all platforms done
    - simulation_round: agent actions for a round
    - simulation_complete: simulation finished
    - prediction_new: new prediction generated
    - prediction_validated: prediction vs reality result
    - health_update: component health change
    - alert: important notification
    """
    queue = event_bus.subscribe()

    async def cleanup_generator():
        try:
            async for event in _event_generator(queue):
                yield event
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Helper functions for other modules to publish events
async def emit_ingestion_progress(platform: str, count: int, total: int) -> None:
    await event_bus.publish("ingestion_progress", {
        "platform": platform,
        "signals_found": count,
        "total_signals": total,
    })


async def emit_simulation_round(
    simulation_id: str, round_num: int, total_rounds: int, actions: int
) -> None:
    await event_bus.publish("simulation_round", {
        "simulation_id": simulation_id,
        "round": round_num,
        "total_rounds": total_rounds,
        "actions_this_round": actions,
    })


async def emit_prediction(prediction_id: str, topic: str, confidence: float) -> None:
    await event_bus.publish("prediction_new", {
        "prediction_id": prediction_id,
        "topic": topic,
        "confidence": confidence,
    })


async def emit_alert(level: str, message: str) -> None:
    await event_bus.publish("alert", {
        "level": level,
        "message": message,
    })
