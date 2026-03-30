"""
Fast candidate generator for two-stage ranking.

Design:
- Lightweight scoring using heuristic blend of recency, engagement velocity,
  platform priors, and quick text/query overlap.
- Intended to downselect thousands of signals to a few hundred.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..shared.types import RawSignal, ScoredSignal
from .features import FeatureBuilder, FeatureVector
from .embeddings import EmbeddingService


class CandidateGenerator:
    def __init__(
        self,
        feature_builder: FeatureBuilder,
        embedder: EmbeddingService | None = None,
        max_candidates: int = 200,
    ):
        self.feature_builder = feature_builder
        self.embedder = embedder or EmbeddingService()
        self.max_candidates = max_candidates

    def rank(
        self,
        signals: List[RawSignal],
        query: str,
        features: Dict[str, FeatureVector],
    ) -> List[Tuple[RawSignal, float]]:
        """Return top candidates with coarse scores."""
        query_embedding = self.embedder.embed_text(query)
        scored: List[Tuple[RawSignal, float]] = []

        for signal in signals:
            f = features.get(signal.id)
            if not f:
                continue

            # Quick similarity via hash-based embeddings
            sim = self.embedder.cosine_similarity(
                query_embedding, self.embedder.embed_text(signal.content[:500])
            )

            # Heuristic score: blend similarity, recency, platform prior, velocity
            score = (
                0.4 * sim
                + 0.25 * f.recency_score
                + 0.2 * min(1.0, f.engagement_velocity / 100.0)
                + 0.15 * f.platform_prior
            )

            scored.append((signal, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: self.max_candidates]
