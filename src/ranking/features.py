"""
Feature extraction helpers for two-stage ranking.

Keeps dependencies minimal and focuses on:
- Recency and freshness (example age)
- Engagement velocity normalization
- Platform priors for trust/quality weighting
- Basic content metadata (length, url presence)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from ..shared.types import RawSignal


DEFAULT_PLATFORM_PRIORS: Dict[str, float] = {
    "reddit": 0.9,
    "hackernews": 0.9,
    "news": 0.85,
    "web": 0.75,
    "twitter": 0.7,
    "bluesky": 0.7,
    "youtube": 0.8,
    "tiktok": 0.6,
    "instagram": 0.6,
    "polymarket": 0.85,
    "moltbook": 0.8,
}


@dataclass
class FeatureVector:
    recency_hours: float
    recency_score: float
    engagement_velocity: float
    platform_prior: float
    text_length: int
    has_url: bool
    cross_platform_count: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "recency_hours": self.recency_hours,
            "recency_score": self.recency_score,
            "engagement_velocity": self.engagement_velocity,
            "platform_prior": self.platform_prior,
            "text_length": self.text_length,
            "has_url": self.has_url,
            "cross_platform_count": self.cross_platform_count,
        }


class FeatureBuilder:
    def __init__(
        self,
        platform_priors: Optional[Dict[str, float]] = None,
        recency_half_life_hours: float = 72.0,
    ):
        self.platform_priors = {**DEFAULT_PLATFORM_PRIORS, **(platform_priors or {})}
        self.recency_half_life_hours = recency_half_life_hours

    def build(
        self,
        signal: RawSignal,
        cross_platform_count: int = 1,
    ) -> FeatureVector:
        hours_old = self._hours_since(signal.timestamp)
        recency_score = math.exp(-0.693 * hours_old / self.recency_half_life_hours)
        engagement = signal.engagement_score()
        velocity = engagement / max(hours_old, 0.5)
        text_len = len(signal.content or "")
        has_url = bool(signal.url)
        platform_prior = self.platform_priors.get(signal.platform.value, 0.5)

        return FeatureVector(
            recency_hours=hours_old,
            recency_score=recency_score,
            engagement_velocity=velocity,
            platform_prior=platform_prior,
            text_length=text_len,
            has_url=has_url,
            cross_platform_count=max(1, cross_platform_count),
        )

    def build_batch(
        self,
        signals: Iterable[RawSignal],
        cross_platform_map: Optional[Dict[str, int]] = None,
    ) -> Dict[str, FeatureVector]:
        cross_platform_map = cross_platform_map or {}
        features: Dict[str, FeatureVector] = {}
        for signal in signals:
            count = cross_platform_map.get(signal.id or "", 1)
            features[signal.id] = self.build(signal, count)
        return features

    def _hours_since(self, timestamp) -> float:
        if timestamp is None:
            return 24.0
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                return 24.0
        delta = datetime.now() - timestamp
        return max(0.1, delta.total_seconds() / 3600)
