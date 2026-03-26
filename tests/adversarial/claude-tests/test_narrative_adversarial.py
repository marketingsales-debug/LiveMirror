"""Adversarial tests for Gemini's NarrativeDNAAnalyzer.
Author: Claude
Purpose: Find gaps in stage identification and fingerprint matching.
"""

import pytest
from src.analysis.narrative.dna import NarrativeDNAAnalyzer
from src.shared.types.prediction import NarrativeStage


class TestNarrativeAdversarial:
    def setup_method(self):
        self.analyzer = NarrativeDNAAnalyzer()

    # --- Stage identification gaps ---

    def test_seed_boundary(self):
        """Exactly at 2 hours and 1000 engagement — which stage?"""
        stage = self.analyzer.identify_stage(age_hours=2, total_engagement=1000, velocity=0.0)
        # Falls through SEED (age >= 2), falls through EARLY_SPREAD (velocity == 0)
        # Falls through COUNTER (velocity not < -0.3), not MAINSTREAM (<100k)
        # Falls through FATIGUE (age < 72)
        # Returns default EARLY_SPREAD — but this is a brand new 2-hour topic
        assert stage in (NarrativeStage.SEED, NarrativeStage.EARLY_SPREAD)

    def test_missing_peak_stage(self):
        """PEAK stage is never returned by identify_stage."""
        # Try conditions that logically should be PEAK:
        # High engagement, moderate age, near-zero velocity (plateau)
        stage = self.analyzer.identify_stage(age_hours=24, total_engagement=80000, velocity=0.02)
        # BUG: No condition matches PEAK — falls through to default EARLY_SPREAD
        assert stage == NarrativeStage.PEAK, \
            f"Expected PEAK for high-engagement plateau, got {stage}"

    def test_missing_resolution_stage(self):
        """RESOLUTION stage is never returned by identify_stage."""
        # Very old, very low velocity, moderate engagement (story resolved)
        stage = self.analyzer.identify_stage(age_hours=200, total_engagement=50000, velocity=0.0)
        # Hits FATIGUE (age > 72, abs(velocity) < 0.1) — close but not RESOLUTION
        # RESOLUTION should be distinct from FATIGUE
        assert stage in (NarrativeStage.FATIGUE, NarrativeStage.RESOLUTION)

    def test_growth_phase_gap(self):
        """Medium age, medium engagement, positive velocity — no condition matches."""
        stage = self.analyzer.identify_stage(age_hours=24, total_engagement=3000, velocity=0.5)
        # Falls through everything, returns EARLY_SPREAD default
        # But 24 hours in with active growth isn't "early spread" — it's growth
        assert stage != NarrativeStage.EARLY_SPREAD, \
            f"24-hour growing topic shouldn't be EARLY_SPREAD"

    def test_mainstream_overrides_everything(self):
        """100k+ engagement always returns MAINSTREAM, even if narrative is dying."""
        stage = self.analyzer.identify_stage(
            age_hours=200, total_engagement=200000, velocity=0.0
        )
        # Hits MAINSTREAM before FATIGUE due to ordering
        # A 200-hour-old, zero-velocity topic with high engagement is actually fatigued
        assert stage == NarrativeStage.MAINSTREAM

    def test_counter_narrative_requires_high_engagement(self):
        """Counter-narrative at low engagement goes undetected."""
        stage = self.analyzer.identify_stage(
            age_hours=6, total_engagement=500, velocity=-0.5
        )
        # velocity < -0.3 but engagement < 20000 → misses COUNTER_NARRATIVE
        # Falls to default EARLY_SPREAD
        assert stage == NarrativeStage.EARLY_SPREAD

    # --- Fingerprint matching gaps ---

    def test_threshold_mismatch_outrage(self):
        """Fingerprint defines outrage at -0.6 velocity, matcher triggers at -0.4."""
        # This means velocities between -0.4 and -0.6 match "outrage" even though
        # the fingerprint template says -0.6
        result = self.analyzer.match_fingerprint(velocity=-0.45, cross_platform=True)
        assert result == "outrage_cascade"
        # Technically this is a false positive based on the fingerprint definition

    def test_threshold_mismatch_viral(self):
        """Fingerprint defines viral_support at 0.5, matcher triggers at 0.4."""
        result = self.analyzer.match_fingerprint(velocity=0.42, cross_platform=False)
        assert result == "viral_support"

    def test_cross_platform_outrage_required(self):
        """Single-platform outrage doesn't match outrage_cascade."""
        result = self.analyzer.match_fingerprint(velocity=-0.7, cross_platform=False)
        assert result != "outrage_cascade"
        # Falls to echo_chamber_loop if velocity < -0.2? No, abs(-0.7) > 0.2
        # Falls to unprecedented_pattern
        assert result == "unprecedented_pattern"

    def test_moderate_velocity_gap(self):
        """Velocity between 0.2 and 0.4 matches nothing specific."""
        result = self.analyzer.match_fingerprint(velocity=0.3, cross_platform=True)
        assert result == "unprecedented_pattern"
        # Many real-world narratives have moderate velocity — they're all "unprecedented"

    def test_negative_moderate_velocity(self):
        """Velocity between -0.2 and -0.4, cross-platform — no match."""
        result = self.analyzer.match_fingerprint(velocity=-0.3, cross_platform=True)
        assert result == "unprecedented_pattern"

    # --- Edge values ---

    def test_zero_everything(self):
        """All zeros should return something reasonable."""
        stage = self.analyzer.identify_stage(0, 0, 0.0)
        assert stage == NarrativeStage.SEED  # brand new with nothing

    def test_negative_age(self):
        """Negative age shouldn't crash."""
        stage = self.analyzer.identify_stage(-1, 100, 0.0)
        # age < 2 → SEED
        assert stage == NarrativeStage.SEED

    def test_extreme_velocity(self):
        """Extreme velocity values should still produce valid fingerprints."""
        result = self.analyzer.match_fingerprint(velocity=-100.0, cross_platform=True)
        assert result == "outrage_cascade"

        result = self.analyzer.match_fingerprint(velocity=100.0, cross_platform=False)
        assert result == "viral_support"

    def test_fingerprint_dict_not_used_by_matcher(self):
        """The historical_fingerprints dict is decoration — matcher uses hardcoded ifs."""
        # Modifying the dict shouldn't change matching behavior
        self.analyzer.historical_fingerprints["outrage_cascade"]["velocity"] = 0.0
        result = self.analyzer.match_fingerprint(velocity=-0.5, cross_platform=True)
        # Still matches because matcher uses hardcoded thresholds, not the dict
        assert result == "outrage_cascade"
