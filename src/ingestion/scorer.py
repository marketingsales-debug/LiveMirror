"""
Signal Scorer — ranks and deduplicates signals from all platforms.
Owner: Claude

Composite scoring based on:
- Text relevance (similarity to query)
- Engagement velocity (engagement per hour since posted)
- Recency (newer = higher score, exponential decay)
- Cross-platform convergence (same topic on multiple platforms = boost)
"""

import math
from typing import List, Dict, Set
from datetime import datetime, timedelta
from collections import defaultdict

from ..shared.types import RawSignal, ScoredSignal


class SignalScorer:
    """Score and rank signals from multiple platforms."""

    def __init__(
        self,
        relevance_weight: float = 0.35,
        engagement_weight: float = 0.25,
        recency_weight: float = 0.20,
        cross_platform_weight: float = 0.20,
        use_embeddings: bool = True,
    ):
        self.relevance_weight = relevance_weight
        self.engagement_weight = engagement_weight
        self.recency_weight = recency_weight
        self.cross_platform_weight = cross_platform_weight

        # Try semantic embeddings, fall back to keyword overlap
        self._semantic = None
        if use_embeddings:
            try:
                from .embeddings import SemanticScorer
                self._semantic = SemanticScorer()
            except Exception:
                pass

    def score_all(
        self,
        signals: List[RawSignal],
        query: str,
    ) -> List[ScoredSignal]:
        """Score all signals and return sorted by composite score."""

        # Deduplicate by content similarity
        unique_signals = self._deduplicate(signals)

        # Detect cross-platform topics
        cross_platform_map = self._detect_cross_platform(unique_signals)

        # Compute max engagement for normalization
        max_engagement = max(
            (s.engagement_score() for s in unique_signals),
            default=1.0,
        ) or 1.0

        scored: List[ScoredSignal] = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Batch compute semantic similarity if available
        semantic_scores = {}
        if self._semantic:
            contents = [s.content for s in unique_signals]
            scores = self._semantic.batch_similarity(query, contents)
            for signal, score in zip(unique_signals, scores):
                semantic_scores[id(signal)] = score

        for signal in unique_signals:
            # Relevance: semantic embeddings (preferred) or keyword overlap (fallback)
            if id(signal) in semantic_scores:
                relevance = semantic_scores[id(signal)]
            else:
                content_lower = signal.content.lower()
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                relevance = min(1.0, overlap / max(len(query_words), 1))

            # Engagement velocity: engagement per hour
            hours_old = self._hours_since(signal.timestamp)
            raw_engagement = signal.engagement_score()
            velocity = raw_engagement / max(hours_old, 0.5)
            normalized_velocity = min(1.0, velocity / (max_engagement / 24))

            # Recency: exponential decay, half-life = 3 days
            recency = math.exp(-0.693 * hours_old / 72)

            # Cross-platform convergence
            platform_key = self._content_key(signal.content)
            cross_count = cross_platform_map.get(platform_key, 1)
            cross_score = min(1.0, (cross_count - 1) / 3)  # 4+ platforms = max

            s = ScoredSignal(
                signal=signal,
                relevance_score=relevance,
                engagement_velocity=normalized_velocity,
                recency_score=recency,
                cross_platform_score=cross_score,
            )
            s.compute_composite(
                self.relevance_weight,
                self.engagement_weight,
                self.recency_weight,
                self.cross_platform_weight,
            )
            scored.append(s)

        scored.sort(key=lambda s: s.composite_score, reverse=True)
        return scored

    def _deduplicate(self, signals: List[RawSignal]) -> List[RawSignal]:
        """Remove near-duplicate signals (same content from same platform)."""
        seen: Set[str] = set()
        unique: List[RawSignal] = []

        for signal in signals:
            key = f"{signal.platform.value}:{self._content_key(signal.content)}"
            if key not in seen:
                seen.add(key)
                unique.append(signal)

        return unique

    def _detect_cross_platform(self, signals: List[RawSignal]) -> Dict[str, int]:
        """Count how many platforms mention similar content."""
        topic_platforms: Dict[str, Set[str]] = defaultdict(set)

        for signal in signals:
            key = self._content_key(signal.content)
            topic_platforms[key].add(signal.platform.value)

        return {key: len(platforms) for key, platforms in topic_platforms.items()}

    def _content_key(self, content: str) -> str:
        """Simple content fingerprint for dedup/cross-platform detection."""
        words = sorted(set(content.lower().split()))[:10]
        return " ".join(words)

    def _hours_since(self, timestamp) -> float:
        """Hours since a timestamp."""
        if timestamp is None:
            return 24.0  # assume 1 day old if unknown
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                return 24.0
        delta = datetime.now() - timestamp
        return max(0.1, delta.total_seconds() / 3600)
