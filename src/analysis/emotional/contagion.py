"""
EmotionalContagionTracker — Sentiment velocity and tipping-point detection.

Fixes applied per Claude's adversarial review:
  - Future timestamps are now filtered out before velocity calculation
  - max_history parameter added to prevent unbounded memory growth (OOM fix)
"""

from datetime import datetime, timezone
from collections import deque
from typing import Deque, Dict, List, Optional


class EmotionalContagionTracker:
    """
    Tracks how fast collective sentiment is shifting and whether a
    tipping point is imminent.

    Args:
        tipping_point_threshold: Velocity magnitude that signals an incoming cascade.
        max_history: Maximum number of entries kept in memory (default 10,000).
                     Oldest entries are evicted when the limit is reached.
    """

    def __init__(
        self,
        tipping_point_threshold: float = 0.4,
        max_history: int = 10_000,
    ):
        self.tipping_point_threshold = tipping_point_threshold
        self.max_history = max_history
        # deque gives O(1) bounded append/pop — key for production stability
        self._history: Deque[Dict] = deque(maxlen=max_history)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_sentiment(
        self,
        text_id: str,
        platform: str,
        sentiment_score: float,
        timestamp: datetime,
    ) -> None:
        """Record a new sentiment observation. Timestamps in the future are dropped."""
        now = datetime.now(tz=timezone.utc)
        # Normalise naive datetimes to UTC for consistent comparison
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Fix: reject future timestamps — they corrupt velocity windows
        if timestamp > now:
            return

        self._history.append({
            "id": text_id,
            "platform": platform,
            "score": sentiment_score,
            "timestamp": timestamp,
        })

    # ------------------------------------------------------------------
    # Velocity
    # ------------------------------------------------------------------

    def calculate_emotional_velocity(self, window_hours: float = 1.0) -> float:
        """
        Rate of change of sentiment over the last `window_hours`.
        Positive → sentiment improving. Negative → sentiment souring.
        Returns 0.0 if not enough data.
        """
        now = datetime.now(tz=timezone.utc)
        cutoff = now.timestamp() - window_hours * 3600

        recent: List[Dict] = [
            x for x in self._history
            if x["timestamp"].timestamp() >= cutoff
        ]

        if len(recent) < 2:
            return 0.0

        recent.sort(key=lambda x: x["timestamp"])
        mid = len(recent) // 2
        first_half = recent[:mid]
        second_half = recent[mid:]

        if not first_half or not second_half:
            return 0.0

        avg_first = sum(x["score"] for x in first_half) / len(first_half)
        avg_second = sum(x["score"] for x in second_half) / len(second_half)

        return avg_second - avg_first

    # ------------------------------------------------------------------
    # Tipping-point detection
    # ------------------------------------------------------------------

    def detect_tipping_point(self, current_velocity: Optional[float] = None) -> bool:
        """
        Returns True if the absolute velocity exceeds the threshold.
        If `current_velocity` is not provided, it is computed automatically.
        """
        velocity = (
            current_velocity
            if current_velocity is not None
            else self.calculate_emotional_velocity()
        )
        return abs(velocity) >= self.tipping_point_threshold

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Flush all recorded history."""
        self._history.clear()

    @property
    def history_size(self) -> int:
        return len(self._history)
