"""
Lightweight embedding helpers for ranking.

This is a deterministic fallback that does not depend on external
models; replace with a real embedding service when available.
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, List


class EmbeddingService:
    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed_text(self, text: str) -> List[float]:
        """Return a deterministic pseudo-embedding (replace with real model)."""
        if not text:
            return [0.0] * self.dim
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vals = [b / 255.0 for b in h]
        # Repeat/crop to target dimension
        vec: List[float] = []
        while len(vec) < self.dim:
            vec.extend(vals)
        return vec[: self.dim]

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
