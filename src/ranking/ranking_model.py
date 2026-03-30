"""
Precise ranking model for the final stage.

Uses richer features and light heuristics for now; replace with a trained
model when available.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from ..shared.types import RawSignal
from .features import FeatureVector


class RankingModel:
    def __init__(self, top_n: int = 50):
        self.top_n = top_n

    def rank(
        self,
        candidates: List[Tuple[RawSignal, float]],
        features: Dict[str, FeatureVector],
    ) -> List[Tuple[RawSignal, float]]:
        """Re-rank candidates with richer feature mix."""
        platform_counts = Counter([c.platform.value for c, _ in candidates])
        ranked: List[Tuple[RawSignal, float]] = []

        for signal, coarse_score in candidates:
            f = features.get(signal.id)
            if not f:
                continue

            # Diversity penalty for platform over-representation
            diversity_penalty = 1.0 / max(1.0, platform_counts[signal.platform.value] ** 0.25)

            # Cross-platform boost
            cross_boost = min(1.0, (f.cross_platform_count - 1) / 3.0)

            # Content length sanity: very short texts get slight penalty
            length_norm = 1.0
            if f.text_length < 40:
                length_norm = 0.85
            elif f.text_length > 800:
                length_norm = 0.9

            score = (
                0.5 * coarse_score
                + 0.2 * f.recency_score
                + 0.15 * min(1.0, f.engagement_velocity / 200.0)
                + 0.1 * cross_boost
                + 0.05 * f.platform_prior
            )
            score *= diversity_penalty * length_norm
            ranked.append((signal, score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[: self.top_n]
