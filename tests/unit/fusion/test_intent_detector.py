"""
Unit tests for IntentDetector.
Owner: Claude
"""

import pytest
from datetime import datetime
from src.fusion.analysis.intent import IntentDetector


class MockSignal:
    """Simple mock for Signal object."""
    def __init__(self, content, timestamp=None):
        self.content = content
        self.timestamp = timestamp or datetime.now()


class TestIntentDetector:
    """Test IntentDetector logic and coordination detection."""

    def test_author_credibility_logic(self):
        """Verify author credibility scoring with highs and lows."""
        detector = IntentDetector()

        meta_low = {
            "account_age_years": 0.1,
            "engagement_rate": 0.0,
            "follower_count": 100,
            "prediction_accuracy": 0.3,
        }
        res_low = detector.analyze_author(meta_low)
        assert 0.2 <= res_low <= 0.6

        meta_high = {
            "account_age_years": 7.0,
            "engagement_rate": 5.0,
            "follower_count": 100,
            "verified": True,
            "prediction_accuracy": 0.8,
        }
        res_high = detector.analyze_author(meta_high)
        assert res_high >= 0.85

    def test_coordination_detection_pump_dump(self):
        """Verify pump-and-dump detection (identical content)."""
        detector = IntentDetector()

        signals = [MockSignal("Buy $MOON now!!! 🚀") for _ in range(10)]

        res = detector.detect_manipulation(signals)
        assert res["is_coordinated"] is True
        assert res["type"] == "pump_and_dump"
        assert res["confidence"] >= 0.65

    def test_coordination_detection_synchronized(self):
        """Verify synchronized posts detection (burst in time)."""
        detector = IntentDetector(burst_window_seconds=180, burst_min_signals=8)

        signals = [
            MockSignal(f"Unique content {i}", timestamp=datetime.fromtimestamp(1700000000 + i))
            for i in range(10)
        ]

        res = detector.detect_manipulation(signals)
        assert res["is_coordinated"] is True
        assert res["type"] == "synchronized_swarms"
        assert res["confidence"] >= 0.8

    def test_intent_classification(self):
        """Verify heuristic intent classification."""
        detector = IntentDetector()
        author_meta = {"account_age_years": 5.1, "engagement_rate": 0.5, "follower_count": 100}

        res_man = detector.determine_intent("HODL TO THE MOON 🚀💎🙌", author_meta)
        assert res_man["intent"] == "manipulative"
        assert 0.4 <= res_man["confidence"] <= 1.0

        res_inf = detector.determine_intent("Official earnings report announced today", author_meta)
        assert res_inf["intent"] == "informational"

        res_edu = detector.determine_intent("Analysis of why market is down due to interest rates", author_meta)
        assert res_edu["intent"] == "educational"

    def test_empty_input_defaults(self):
        """Graceful handling of empty text."""
        detector = IntentDetector()
        res = detector.determine_intent("", {})
        assert res["intent"] == "informational"
        assert res["confidence"] == 0.4
