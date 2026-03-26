"""Adversarial tests for Gemini's EmotionalContagionTracker.
Author: Claude
Purpose: Break the velocity calculator and tipping point detector.
Updated: Adapted for Gemini's bugfix (deque, future-timestamp guard, UTC).
"""

import pytest
from datetime import datetime, timedelta, timezone
from src.analysis.emotional.contagion import EmotionalContagionTracker


class TestContagionAdversarial:
    def setup_method(self):
        self.tracker = EmotionalContagionTracker()

    # --- Velocity calculation edge cases ---

    def test_single_entry_returns_zero(self):
        """One data point can't have velocity."""
        now = datetime.now(tz=timezone.utc)
        self.tracker.record_sentiment("a", "reddit", 0.5, now)
        vel = self.tracker.calculate_emotional_velocity()
        assert vel == 0.0

    def test_two_entries_minimum(self):
        """Two entries should produce non-zero velocity if scores differ."""
        now = datetime.now(tz=timezone.utc)
        self.tracker.record_sentiment("a", "reddit", -1.0, now - timedelta(minutes=30))
        self.tracker.record_sentiment("b", "reddit", 1.0, now - timedelta(minutes=5))
        vel = self.tracker.calculate_emotional_velocity()
        assert vel > 0.0, f"Expected positive velocity, got {vel}"

    def test_all_same_score_zero_velocity(self):
        """Constant sentiment should produce zero velocity."""
        now = datetime.now(tz=timezone.utc)
        for i in range(10):
            self.tracker.record_sentiment(
                f"s{i}", "reddit", 0.5, now - timedelta(minutes=60 - i * 5)
            )
        vel = self.tracker.calculate_emotional_velocity()
        assert vel == pytest.approx(0.0, abs=0.01)

    def test_old_entries_excluded_from_window(self):
        """Entries outside the time window should be ignored."""
        now = datetime.now(tz=timezone.utc)
        # Old entries: very positive
        for i in range(10):
            self.tracker.record_sentiment(
                f"old{i}", "reddit", 1.0, now - timedelta(hours=10)
            )
        # Recent entries: very negative
        for i in range(10):
            self.tracker.record_sentiment(
                f"new{i}", "reddit", -0.8, now - timedelta(minutes=i * 5)
            )
        vel = self.tracker.calculate_emotional_velocity(window_hours=1)
        # Should reflect only the recent entries
        assert abs(vel) < 0.5, f"Old entries leaked into velocity: {vel}"

    # --- Memory management ---

    def test_bounded_memory_with_deque(self):
        """Tracker should cap history at max_history."""
        tracker = EmotionalContagionTracker(max_history=100)
        now = datetime.now(tz=timezone.utc)
        for i in range(200):
            tracker.record_sentiment(f"s{i}", "reddit", 0.0, now - timedelta(seconds=i))
        assert tracker.history_size <= 100

    # --- Tipping point ---

    def test_tipping_point_at_exact_threshold(self):
        """Velocity exactly at threshold should trigger."""
        assert self.tracker.detect_tipping_point(0.4) is True
        assert self.tracker.detect_tipping_point(-0.4) is True

    def test_tipping_point_just_below_threshold(self):
        """Velocity just below threshold should NOT trigger."""
        assert self.tracker.detect_tipping_point(0.39) is False
        assert self.tracker.detect_tipping_point(-0.39) is False

    def test_tipping_point_zero_velocity(self):
        """Zero velocity is never a tipping point."""
        assert self.tracker.detect_tipping_point(0.0) is False

    # --- Datetime edge cases ---

    def test_future_timestamps_rejected(self):
        """Future timestamps should be silently dropped."""
        now = datetime.now(tz=timezone.utc)
        self.tracker.record_sentiment("a", "reddit", 0.5, now + timedelta(hours=10))
        assert self.tracker.history_size == 0, "Future timestamps should be rejected"

    def test_identical_timestamps(self):
        """All entries at the exact same time should handle gracefully."""
        now = datetime.now(tz=timezone.utc)
        for i in range(10):
            self.tracker.record_sentiment(
                f"s{i}", "reddit", float(i) / 10.0, now - timedelta(seconds=1)
            )
        vel = self.tracker.calculate_emotional_velocity()
        assert isinstance(vel, float)

    # --- Custom threshold ---

    def test_custom_threshold(self):
        """Custom tipping point threshold should be respected."""
        sensitive = EmotionalContagionTracker(tipping_point_threshold=0.1)
        assert sensitive.detect_tipping_point(0.15) is True

        insensitive = EmotionalContagionTracker(tipping_point_threshold=0.9)
        assert insensitive.detect_tipping_point(0.5) is False

    # --- Clear ---

    def test_clear_resets_history(self):
        """clear() should empty all history."""
        now = datetime.now(tz=timezone.utc)
        self.tracker.record_sentiment("a", "reddit", 0.5, now)
        self.tracker.clear()
        assert self.tracker.history_size == 0
