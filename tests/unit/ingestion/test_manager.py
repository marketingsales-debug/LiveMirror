"""Tests for IngestionManager — parallel platform search."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.shared.types import RawSignal, Platform, SignalType
from src.ingestion.manager import IngestionManager
from src.ingestion.base import BaseIngester


class MockIngester(BaseIngester):
    """Mock ingester for testing."""

    def __init__(self, platform: Platform, signals: list = None, should_fail: bool = False):
        self.platform = platform
        self._signals = signals or []
        self._should_fail = should_fail

    async def search(self, query, since=None, max_results=100):
        if self._should_fail:
            raise ConnectionError(f"{self.platform.value} is down")
        return self._signals

    async def health_check(self):
        return not self._should_fail


def _make_signal(platform: Platform, content: str) -> RawSignal:
    return RawSignal(
        platform=platform,
        signal_type=SignalType.SOCIAL_POST,
        content=content,
        engagement={"likes": 0, "comments": 0, "shares": 0},
    )


class TestIngestionManager:
    def setup_method(self):
        self.manager = IngestionManager()

    @pytest.mark.asyncio
    async def test_register_and_list_platforms(self):
        self.manager.register(MockIngester(Platform.REDDIT))
        self.manager.register(MockIngester(Platform.HACKERNEWS))
        assert Platform.REDDIT in self.manager.available_platforms
        assert Platform.HACKERNEWS in self.manager.available_platforms

    @pytest.mark.asyncio
    async def test_ingest_all_aggregates(self):
        self.manager.register(MockIngester(
            Platform.REDDIT,
            [_make_signal(Platform.REDDIT, "reddit post")]
        ))
        self.manager.register(MockIngester(
            Platform.HACKERNEWS,
            [_make_signal(Platform.HACKERNEWS, "hn story")]
        ))

        results = await self.manager.ingest_all("test query")
        assert len(results) == 2
        platforms = {s.platform for s in results}
        assert Platform.REDDIT in platforms
        assert Platform.HACKERNEWS in platforms

    @pytest.mark.asyncio
    async def test_handles_platform_failure_gracefully(self):
        self.manager.register(MockIngester(
            Platform.REDDIT,
            [_make_signal(Platform.REDDIT, "works")]
        ))
        self.manager.register(MockIngester(
            Platform.TWITTER,
            should_fail=True,
        ))

        results = await self.manager.ingest_all("test")
        # Should still return Reddit results despite Twitter failure
        assert len(results) == 1
        assert results[0].platform == Platform.REDDIT

    @pytest.mark.asyncio
    async def test_filter_by_platform(self):
        self.manager.register(MockIngester(
            Platform.REDDIT,
            [_make_signal(Platform.REDDIT, "reddit")]
        ))
        self.manager.register(MockIngester(
            Platform.HACKERNEWS,
            [_make_signal(Platform.HACKERNEWS, "hn")]
        ))

        results = await self.manager.ingest_all("test", platforms=[Platform.REDDIT])
        assert len(results) == 1
        assert results[0].platform == Platform.REDDIT

    @pytest.mark.asyncio
    async def test_empty_when_no_ingesters(self):
        results = await self.manager.ingest_all("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        self.manager.register(MockIngester(Platform.REDDIT))
        self.manager.register(MockIngester(Platform.TWITTER, should_fail=True))

        health = await self.manager.health_check_all()
        assert health["reddit"] is True
        assert health["twitter"] is False
