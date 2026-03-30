"""
Ingestion Manager — orchestrates parallel data collection from all platforms.
Owner: Claude
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from ..shared.types import RawSignal, Platform
from .base import BaseIngester


class IngestionManager:
    """
    Manages parallel ingestion from all configured platforms.
    Inspired by last30days' parallel search architecture.
    """

    def __init__(self):
        self._ingesters: Dict[Platform, BaseIngester] = {}

    def register(self, ingester: BaseIngester) -> None:
        """Register a platform ingester."""
        self._ingesters[ingester.platform] = ingester

    @property
    def available_platforms(self) -> List[Platform]:
        return list(self._ingesters.keys())

    async def ingest_all(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        since: Optional[datetime] = None,
        max_results_per_platform: int = 100,
    ) -> List[RawSignal]:
        """
        Search all platforms in parallel.

        Args:
            query: Search query
            platforms: Specific platforms (None = all registered)
            since: Time window start
            max_results_per_platform: Max results per platform

        Returns:
            Aggregated list of RawSignal from all platforms
        """
        targets = platforms or self.available_platforms
        active = {p: self._ingesters[p] for p in targets if p in self._ingesters}

        if not active:
            return []

        # Parallel search across all platforms
        tasks = [
            ingester.search(query, since, max_results_per_platform)
            for ingester in active.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals: List[RawSignal] = []
        for platform, result in zip(active.keys(), results):
            if isinstance(result, Exception):
                print(f"[IngestionManager] {platform.value} failed: {result}")
                continue
            signals.extend(result)

        return signals

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all registered ingesters."""
        results = {}
        for platform, ingester in self._ingesters.items():
            try:
                results[platform.value] = await ingester.health_check()
            except Exception:
                results[platform.value] = False
        return results
