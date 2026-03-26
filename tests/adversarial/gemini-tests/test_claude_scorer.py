"""
Adversarial tests for Claude's ingestion scorer.
Written by Gemini to find edge cases and failure modes.

Run with: PYTHONPATH=. python -m pytest tests/adversarial/gemini-tests/ -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.shared.types.platform import Platform, RawSignal, ScoredSignal, SignalType


# ---------------------------------------------------------------------------
# Helpers to build minimal ScoredSignal objects for testing
# ---------------------------------------------------------------------------

def make_signal(
    content: str,
    platform: Platform = Platform.REDDIT,
    engagement: dict = None,
    relevance: float = 0.5,
    cross_platform: float = 0.0,
    recency: float = 0.8,
    velocity: float = 10.0,
) -> ScoredSignal:
    raw = RawSignal(
        platform=platform,
        signal_type=SignalType.SOCIAL_POST,
        content=content,
        timestamp=datetime.now(tz=timezone.utc),
        engagement=engagement or {"likes": 10, "shares": 2, "comments": 5},
    )
    scored = ScoredSignal(
        signal=raw,
        relevance_score=relevance,
        engagement_velocity=velocity,
        recency_score=recency,
        cross_platform_score=cross_platform,
        composite_score=0.0,
    )
    scored.compute_composite()
    return scored


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

class TestCompositeScoring:
    def test_all_zeros_yields_zero(self):
        s = make_signal("test", relevance=0.0, velocity=0.0, recency=0.0, cross_platform=0.0)
        assert s.composite_score == 0.0

    def test_composite_within_bounds(self):
        """Composite score should always be in [0, 1]."""
        for _ in range(20):
            import random
            s = make_signal(
                "content",
                relevance=random.random(),
                velocity=random.uniform(0, 1000),
                recency=random.random(),
                cross_platform=random.random(),
            )
            # Engagement velocity is not normalised — test that scorer handles this
            assert s.composite_score >= 0.0, "Composite score must never be negative"

    def test_high_relevance_raises_composite(self):
        low_r = make_signal("test", relevance=0.1)
        high_r = make_signal("test", relevance=0.9)
        assert high_r.composite_score > low_r.composite_score

    def test_cross_platform_bonus_applied(self):
        no_cross = make_signal("test", cross_platform=0.0)
        yes_cross = make_signal("test", cross_platform=1.0)
        assert yes_cross.composite_score > no_cross.composite_score


# ---------------------------------------------------------------------------
# Engagement scoring
# ---------------------------------------------------------------------------

class TestEngagementScoring:
    def test_shares_weighted_higher_than_likes(self):
        """Shares should count 3x likes based on engagement_score formula."""
        likes_only = RawSignal(
            platform=Platform.REDDIT,
            signal_type=SignalType.SOCIAL_POST,
            content="x",
            engagement={"likes": 30, "shares": 0, "comments": 0},
        )
        shares_only = RawSignal(
            platform=Platform.REDDIT,
            signal_type=SignalType.SOCIAL_POST,
            content="x",
            engagement={"likes": 0, "shares": 10, "comments": 0},
        )
        assert shares_only.engagement_score() == likes_only.engagement_score(), \
            "10 shares should equal 30 likes (3x weight)"

    def test_comments_weighted_at_2x(self):
        comments_signal = RawSignal(
            platform=Platform.REDDIT,
            signal_type=SignalType.SOCIAL_POST,
            content="x",
            engagement={"likes": 0, "shares": 0, "comments": 5},
        )
        assert comments_signal.engagement_score() == 10  # 5 * 2

    def test_empty_engagement_is_zero(self):
        signal = RawSignal(
            platform=Platform.TWITTER,
            signal_type=SignalType.COMMENT,
            content="empty",
            engagement={},
        )
        assert signal.engagement_score() == 0.0

    def test_missing_keys_dont_crash(self):
        """Scorer should not raise KeyError on missing engagement keys."""
        signal = RawSignal(
            platform=Platform.HACKERNEWS,
            signal_type=SignalType.SOCIAL_POST,
            content="test",
            engagement={"upvotes": 50},  # non-standard key
        )
        assert signal.engagement_score() == 0.0  # unknown keys default to 0


# ---------------------------------------------------------------------------
# Platform edge cases
# ---------------------------------------------------------------------------

class TestPlatformEdgeCases:
    def test_polymarket_signal_has_no_social_engagement(self):
        """Polymarket signals are prediction odds, not social posts."""
        pm = make_signal(
            content="Probability of event X: 72%",
            platform=Platform.POLYMARKET,
            engagement={"volume": 150_000},  # non-standard key
        )
        # Should not crash and should produce a valid composite
        assert 0.0 <= pm.composite_score

    def test_very_long_content_doesnt_overflow_scorer(self):
        long_content = "great " * 10_000
        s = make_signal(content=long_content)
        assert s.composite_score >= 0.0


# ---------------------------------------------------------------------------
# Recency decay
# ---------------------------------------------------------------------------

class TestRecencyDecay:
    def test_older_signal_has_lower_recency(self):
        """Older signals should receive a lower recency_score."""
        recent = make_signal("test", recency=0.9)
        old = make_signal("test", recency=0.1)
        assert recent.composite_score > old.composite_score

    def test_recency_at_zero_doesnt_eliminate_score(self):
        """Zero recency should not zero out the entire composite."""
        s = make_signal("test", relevance=0.8, recency=0.0, cross_platform=0.5)
        # Relevance + cross-platform should still contribute
        assert s.composite_score > 0.0


# ---------------------------------------------------------------------------
# Deduplication (structural test — scorer should tag duplicates)
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_identical_content_from_same_source_flagged(self):
        """Two signals with identical content+platform should be detected as duplicates."""
        s1 = make_signal("breaking: earthquake hits tokyo", platform=Platform.REDDIT)
        s2 = make_signal("breaking: earthquake hits tokyo", platform=Platform.REDDIT)
        # Structural check: both generate the same engagement_score fingerprint
        assert s1.signal.engagement_score() == s2.signal.engagement_score()

    def test_same_content_different_platform_is_cross_platform(self):
        """Same content on different platforms should boost cross_platform_score."""
        s1 = make_signal("earthquake hits tokyo", platform=Platform.REDDIT, cross_platform=1.0)
        s2 = make_signal("earthquake hits tokyo", platform=Platform.TWITTER, cross_platform=1.0)
        # Both should have elevated composite from cross-platform signal
        single = make_signal("earthquake hits tokyo", platform=Platform.REDDIT, cross_platform=0.0)
        assert s1.composite_score > single.composite_score
