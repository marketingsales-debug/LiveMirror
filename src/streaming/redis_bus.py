"""
Redis-backed Event Bus for multi-worker SSE support.
Owner: Claude

The in-memory EventBus in stream.py works for single-worker deploys.
This module adds Redis pub/sub so multiple uvicorn workers can share
events. Falls back gracefully to in-memory if Redis is unavailable.

Usage:
    bus = RedisEventBus()
    await bus.connect()  # connects to Redis or falls back to in-memory
    await bus.publish("simulation_round", {...})
    queue = bus.subscribe()
    msg = await queue.get()
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime


class RedisEventBus:
    """
    Event bus with Redis pub/sub backend for multi-worker SSE.

    Falls back to in-memory queues if Redis is not available,
    so the app works identically in dev (single worker) and
    prod (multi-worker with Redis).
    """

    CHANNEL = "livemirror:events"

    def __init__(self):
        self._redis = None
        self._pubsub = None
        self._subscribers: list[asyncio.Queue] = []
        self._listener_task: Optional[asyncio.Task] = None
        self._connected = False
        self._logger = logging.getLogger(__name__)

    async def connect(self) -> bool:
        """
        Connect to Redis. Returns True if connected, False if falling back.
        """
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(self.CHANNEL)
            self._connected = True

            # Start listener task
            self._listener_task = asyncio.create_task(self._listen())
            self._logger.info("[RedisEventBus] Connected to %s", redis_url)
            return True

        except Exception as e:
            self._logger.warning("[RedisEventBus] Redis unavailable (%s), using in-memory fallback", e)
            self._redis = None
            self._connected = False
            return False

    @property
    def is_redis_connected(self) -> bool:
        return self._connected

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
        """
        Publish an event. Goes through Redis if connected,
        otherwise directly to in-memory subscribers.
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        if self._connected and self._redis:
            # Publish to Redis — all workers receive it
            try:
                await self._redis.publish(self.CHANNEL, json.dumps(message, default=str))
                return
            except Exception as e:
                self._logger.warning("[RedisEventBus] Publish failed (%s), falling back to in-memory", e)

        # In-memory fallback
        self._dispatch_to_subscribers(message)

    async def _listen(self) -> None:
        """Listen for Redis messages and dispatch to local subscribers."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    self._dispatch_to_subscribers(data)
                except json.JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception:
            self._logger.exception("[RedisEventBus] Listener error")
            self._connected = False

    def _dispatch_to_subscribers(self, message: Dict[str, Any]) -> None:
        """Push message to all local subscriber queues."""
        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                self._logger.warning("SSE queue overflow; dropping oldest message")
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
        for q in dead_queues:
            self._subscribers.remove(q)

    async def close(self) -> None:
        """Clean shutdown."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.unsubscribe(self.CHANNEL)
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()

        self._connected = False
