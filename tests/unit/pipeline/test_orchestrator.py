"""Tests for LiveMirrorPipeline — end-to-end orchestration."""

import pytest
from datetime import datetime, timedelta

from src.shared.types import RawSignal, Platform, SignalType
from src.pipeline.orchestrator import LiveMirrorPipeline
from src.ingestion.base import BaseIngester


class MockIngester(BaseIngester):
    def __init__(self, platform, signals=None):
        self.platform = platform
        self._signals = signals or []

    async def search(self, query, since=None, max_results=100):
        return self._signals

    async def health_check(self):
        return True


def _make_signals():
    """Create a small set of realistic test signals."""
    return [
        RawSignal(
            platform=Platform.REDDIT,
            signal_type=SignalType.SOCIAL_POST,
            content="SEC announces new AI regulation framework",
            engagement={"likes": 500, "comments": 200, "shares": 50},
            timestamp=datetime.now() - timedelta(hours=2),
        ),
        RawSignal(
            platform=Platform.HACKERNEWS,
            signal_type=SignalType.SOCIAL_POST,
            content="AI regulation is coming — SEC announces framework",
            engagement={"likes": 300, "comments": 100, "shares": 20},
            timestamp=datetime.now() - timedelta(hours=1),
        ),
        RawSignal(
            platform=Platform.TWITTER,
            signal_type=SignalType.SOCIAL_POST,
            content="This AI regulation is terrible for innovation",
            engagement={"likes": 2000, "comments": 800, "shares": 500},
            timestamp=datetime.now() - timedelta(minutes=30),
        ),
    ]


class TestLiveMirrorPipeline:
    def setup_method(self):
        self.pipeline = LiveMirrorPipeline()

    @pytest.mark.asyncio
    async def test_full_pipeline_run(self):
        """End-to-end: ingest → score → analyze → graph."""
        signals = _make_signals()
        self.pipeline.register_ingester(
            MockIngester(Platform.REDDIT, [signals[0]])
        )
        self.pipeline.register_ingester(
            MockIngester(Platform.HACKERNEWS, [signals[1]])
        )
        self.pipeline.register_ingester(
            MockIngester(Platform.TWITTER, [signals[2]])
        )

        result = await self.pipeline.run("AI regulation", emit_events=False)

        assert result["query"] == "AI regulation"
        assert len(result["scored_signals"]) >= 2
        assert len(result["analysis_results"]) >= 2
        assert result["graph_stats"]["entities_created"] >= 1
        assert result["timing"]["ingestion_ms"] >= 0

    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        """Pipeline with no ingesters returns empty results."""
        result = await self.pipeline.run("test", emit_events=False)
        assert result["scored_signals"] == []
        assert result["analysis_results"] == []

    @pytest.mark.asyncio
    async def test_graph_populated(self):
        """Graph should have entities after pipeline run."""
        signals = _make_signals()
        self.pipeline.register_ingester(
            MockIngester(Platform.REDDIT, signals)
        )

        await self.pipeline.run("AI regulation", emit_events=False)
        assert self.pipeline.graph.entity_count > 0
        assert self.pipeline.graph.edge_count > 0

    @pytest.mark.asyncio
    async def test_analysis_produces_sentiment(self):
        """Analysis results should have non-trivial sentiment scores."""
        self.pipeline.register_ingester(
            MockIngester(Platform.TWITTER, [
                RawSignal(
                    platform=Platform.TWITTER,
                    signal_type=SignalType.SOCIAL_POST,
                    content="This is absolutely terrible and horrible news",
                    engagement={"likes": 100, "comments": 50, "shares": 10},
                    timestamp=datetime.now() - timedelta(hours=1),
                ),
            ])
        )

        result = await self.pipeline.run("terrible news", emit_events=False)
        if result["analysis_results"]:
            ar = result["analysis_results"][0]
            assert ar.sentiment_score < 0, f"Expected negative sentiment, got {ar.sentiment_score}"

    @pytest.mark.asyncio
    async def test_stats_populated_after_run(self):
        """Pipeline.stats should reflect the last run."""
        self.pipeline.register_ingester(
            MockIngester(Platform.REDDIT, _make_signals()[:1])
        )
        await self.pipeline.run("test", emit_events=False)
        stats = self.pipeline.stats
        assert stats["query"] == "test"
        assert stats["raw_signals"] >= 1
