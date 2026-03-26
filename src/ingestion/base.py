"""
Base ingestion interface.
All platform scrapers implement this.
Owner: Claude
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timedelta

from ..shared.types import RawSignal, Platform


class BaseIngester(ABC):
    """Base class for all platform ingesters."""

    platform: Platform

    @abstractmethod
    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 100,
    ) -> List[RawSignal]:
        """
        Search a platform for signals matching a query.

        Args:
            query: Search query
            since: Only return results after this time (default: 30 days ago)
            max_results: Maximum number of results

        Returns:
            List of RawSignal from this platform
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the platform API is accessible."""
        ...

    def default_since(self) -> datetime:
        """Default time window: 30 days ago."""
        return datetime.now() - timedelta(days=30)
