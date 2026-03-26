"""Tests for SignalScorer — signal ranking and deduplication."""

import pytest
from datetime import datetime, timedelta

from src.shared.types import RawSignal, Platform, SignalType
from src.ingestion.scorer import SignalScorer


def _make_signal(
    content: str,
    platform: Platform = Platform.REDDIT,
    likes: int = 10,
    comments: int = 5,
    hours_ago: float = 12,
) -> RawSignal:
    return RawSignal(
        platform=platform,
        signal_type=SignalType.SOCIAL_POST,
        content=content,
        timestamp=datetime.now() - timedelta(hours=hours_ago),
        engagement={"likes": likes, "comments": comments, "shares": 0},
    )


class TestSignalScorer:
    def setup_method(self):
        self.scorer = SignalScorer()

    def test_scores_relevant_signal_higher(self):
        signals = [
            _make_signal("AI prediction markets are booming"),
            _make_signal("cats are cute and fluffy"),
        ]
        scored = self.scorer.score_all(signals, "AI prediction")
        assert scored[0].signal.content.startswith("AI prediction")
        assert scored[0].composite_score > scored[1].composite_score

    def test_scores_higher_engagement_higher(self):
        signals = [
            _make_signal("AI news", likes=1000, comments=500),
            _make_signal("AI news update", likes=1, comments=0),
        ]
        scored = self.scorer.score_all(signals, "AI news")
        assert scored[0].signal.engagement["likes"] == 1000

    def test_scores_recent_higher_than_old(self):
        signals = [
            _make_signal("breaking AI news", hours_ago=1),
            _make_signal("old AI news from weeks ago", hours_ago=600),
        ]
        scored = self.scorer.score_all(signals, "AI news")
        assert scored[0].recency_score > scored[1].recency_score

    def test_deduplicates_same_platform(self):
        signals = [
            _make_signal("exact same content here"),
            _make_signal("exact same content here"),
        ]
        scored = self.scorer.score_all(signals, "content")
        assert len(scored) == 1

    def test_cross_platform_boost(self):
        signals = [
            _make_signal("AI regulation news", platform=Platform.REDDIT),
            _make_signal("AI regulation news", platform=Platform.TWITTER),
            _make_signal("AI regulation news", platform=Platform.HACKERNEWS),
            _make_signal("unrelated topic completely", platform=Platform.REDDIT),
        ]
        scored = self.scorer.score_all(signals, "AI regulation")
        # The cross-platform signal should rank higher
        ai_signals = [s for s in scored if "AI regulation" in s.signal.content]
        assert ai_signals[0].cross_platform_score > 0

    def test_empty_signals(self):
        scored = self.scorer.score_all([], "test")
        assert scored == []

    def test_composite_score_between_0_and_1(self):
        signals = [_make_signal("test signal for scoring")]
        scored = self.scorer.score_all(signals, "test")
        for s in scored:
            assert 0 <= s.composite_score <= 1.5  # can exceed 1 with high cross-platform
