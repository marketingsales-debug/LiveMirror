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
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class EventBus:
    """
    Simple in-memory event bus for SSE.
    Components push events, SSE endpoint streams them to frontend.
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Create a new subscriber queue."""
        # Increased from 100 to 500 to handle burst of analysis events
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
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
                logger.warning("SSE queue overflow; dropping oldest message")
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                overflow_message = {
                    "type": "alert",
                    "data": {
                        "level": "warning",
                        "message": "SSE client is lagging; messages were dropped.",
                        "queue_size": queue.qsize(),
                    },
                    "timestamp": datetime.now().isoformat(),
                }
                try:
                    queue.put_nowait(overflow_message)
                except asyncio.QueueFull:
                    dead_queues.append(queue)

        # Clean up overflowed queues
        for q in dead_queues:
            self._subscribers.remove(q)


# Global event bus — uses Redis when available, in-memory fallback.
# The RedisEventBus has the same interface as EventBus, so all
# emit_* helpers work identically regardless of backend.
_redis_bus = None

def _get_event_bus():
    """Get or create the event bus (Redis-backed if available)."""
    global _redis_bus
    if _redis_bus is not None:
        return _redis_bus

    # Check if this file is already loaded under a different name
    # e.g. "app.api.stream" vs "backend.app.api.stream"
    import sys
    import os
    this_file = os.path.abspath(__file__).rstrip("c")
    for name, module in list(sys.modules.items()):
        if (
            module
            and hasattr(module, "__file__")
            and module.__file__
            and os.path.abspath(module.__file__).rstrip("c") == this_file
        ):
            if hasattr(module, "event_bus") and module is not sys.modules[__name__]:
                _redis_bus = module.event_bus
                return _redis_bus

    try:
        from src.streaming.redis_bus import RedisEventBus
        _redis_bus = RedisEventBus()
        # Connection happens async in lifespan — for now return it
        return _redis_bus
    except (ImportError, ModuleNotFoundError):
        _redis_bus = EventBus()
        return _redis_bus

event_bus = _get_event_bus()


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
    
    Ingestion:
    - ingestion_progress: signals found per platform
    - ingestion_complete: all platforms done
    
    Analysis:
    - analysis_result: sentiment/contagion/narrative analysis for a signal
    - graph_update: knowledge graph entity/edge counts
    - fusion_result: multimodal fusion consensus
    
    Simulation:
    - simulation_round: agent actions for a round
    - simulation_complete: simulation finished
    
    Prediction:
    - prediction_new: new prediction generated
    - prediction_validated: prediction vs reality result
    - audience_prediction: segment-specific prediction
    - temporal_update: momentum/velocity/acceleration
    
    Fine-Tuning:
    - fine_tune_started: loop begins with sample count
    - fine_tune_progress: epoch progress with loss/accuracy
    - fine_tune_completed: success or rollback notification
    - accuracy_drift: model drift warning/critical alert
    
    Autonomous Agent:
    - agent_thought: status/thoughts from coding agent
    - agent_action: file write or shell execution
    
    System:
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


@router.get("/debug")
async def debug_event_bus():
    """Debug endpoint to check event bus state."""
    import sys
    return {
        "event_bus_type": type(event_bus).__name__,
        "event_bus_id": id(event_bus),
        "subscribers": len(event_bus._subscribers),
        "module_name": __name__,
        "sys_path": sys.path,
        "sys_modules_stream": [k for k in sys.modules if "stream" in k],
    }


# Helper functions for other modules to publish events
async def emit_ingestion_progress(platform: str, count: int, total: int) -> None:
    await event_bus.publish("ingestion_progress", {
        "platform": platform,
        "signals_found": count,
        "total_signals": total,
    })


async def emit_simulation_round(
    simulation_id: str,
    round_num: int,
    total_rounds: int,
    actions: int,
    trust_network: Optional[Dict[str, Any]] = None,
    belief_profile: Optional[Dict[int, float]] = None,
) -> None:
    await event_bus.publish("simulation_round", {
        "simulation_id": simulation_id,
        "round": round_num,
        "total_rounds": total_rounds,
        "actions_this_round": actions,
        "trust_network": trust_network,
        "belief_profile": belief_profile,
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


async def emit_analysis_result(
    signal_id: str,
    platform: str,
    sentiment_score: float,
    emotional_velocity: float,
    is_tipping_point: bool,
    narrative_stage: str,
    fingerprint: str,
) -> None:
    """Emit an AnalysisResult from Gemini's pipeline to the frontend."""
    await event_bus.publish("analysis_result", {
        "signal_id": signal_id,
        "platform": platform,
        "sentiment_score": sentiment_score,
        "emotional_velocity": emotional_velocity,
        "is_tipping_point": is_tipping_point,
        "narrative_stage": narrative_stage,
        "fingerprint": fingerprint,
    })


async def emit_graph_update(
    entities_created: int,
    edges_created: int,
    total_entities: int,
    total_edges: int,
) -> None:
    """Emit knowledge graph ingestion stats."""
    await event_bus.publish("graph_update", {
        "entities_created": entities_created,
        "edges_created": edges_created,
        "total_entities": total_entities,
        "total_edges": total_edges,
    })


async def emit_ingestion_complete(
    query: str,
    total_signals: int,
    platforms_searched: int,
    top_score: float,
) -> None:
    """Emit when all platforms have been searched for a query."""
    await event_bus.publish("ingestion_complete", {
        "query": query,
        "total_signals": total_signals,
        "platforms_searched": platforms_searched,
        "top_composite_score": top_score,
    })


async def emit_agent_thought(message: str, step: str = "thinking") -> None:
    """Emit a thought from the autonomous coding agent."""
    await event_bus.publish("agent_thought", {
        "message": message,
        "step": step,
    })


async def emit_agent_action(action_type: str, details: Dict[str, Any]) -> None:
    """Emit an action (WRITE_FILE / EXEC) taken by the agent."""
    await event_bus.publish("agent_action", {
        "action_type": action_type,
        "details": details,
    })


async def emit_fusion_result(
    signal_id: str,
    direction: float,
    confidence: float,
    modalities: list[str],
) -> None:
    """Emit multimodal fusion consensus for a signal."""
    await event_bus.publish("fusion_result", {
        "signal_id": signal_id,
        "direction": direction,
        "confidence": confidence,
        "modalities": modalities,
    })


async def emit_audience_prediction(
    segment: str,
    direction: float,
    confidence: float,
) -> None:
    """Emit a prediction for a specific audience segment."""
    await event_bus.publish("audience_prediction", {
        "segment": segment,
        "direction": direction,
        "confidence": confidence,
    })


async def emit_temporal_update(
    momentum: float,
    velocity: float,
    acceleration: float,
) -> None:
    """Emit system-wide temporal dynamic updates."""
    await event_bus.publish("temporal_update", {
        "momentum": momentum,
        "velocity": velocity,
        "acceleration": acceleration,
    })


# ============================================
# Fine-Tuning Loop SSE Events
# ============================================

async def emit_fine_tune_started(
    run_id: str,
    samples: int,
    epochs: int,
) -> None:
    """Emit when fine-tuning loop starts."""
    await event_bus.publish("fine_tune_started", {
        "run_id": run_id,
        "samples": samples,
        "epochs": epochs,
    })


async def emit_fine_tune_progress(
    run_id: str,
    epoch: int,
    total_epochs: int,
    loss: float,
    accuracy: float,
) -> None:
    """Emit fine-tuning progress updates."""
    await event_bus.publish("fine_tune_progress", {
        "run_id": run_id,
        "epoch": epoch,
        "total_epochs": total_epochs,
        "loss": loss,
        "accuracy": accuracy,
        "progress_pct": round(epoch / total_epochs * 100, 1),
    })


async def emit_fine_tune_completed(
    run_id: str,
    samples: int,
    pre_accuracy: float,
    post_accuracy: float,
    improvement: float,
    rollback: bool = False,
) -> None:
    """Emit when fine-tuning completes (success or rollback)."""
    await event_bus.publish("fine_tune_completed", {
        "run_id": run_id,
        "samples": samples,
        "pre_accuracy": pre_accuracy,
        "post_accuracy": post_accuracy,
        "improvement": improvement,
        "rollback": rollback,
        "status": "rollback" if rollback else "success",
    })


async def emit_accuracy_drift_alert(
    current_accuracy: float,
    baseline_accuracy: float,
    drift_magnitude: float,
    severity: str,
) -> None:
    """Emit accuracy drift alert for monitoring."""
    await event_bus.publish("accuracy_drift", {
        "current_accuracy": current_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "drift_magnitude": drift_magnitude,
        "severity": severity,  # "warning", "critical"
    })
