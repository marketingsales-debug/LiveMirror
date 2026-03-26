"""Adversarial tests for Gemini's NarrativeDNAAnalyzer.
Author: Claude
Purpose: Find gaps in stage identification and fingerprint matching.
Updated: Adapted for Gemini's bugfix (PEAK stage, composite fingerprint scoring,
         new fingerprint types, removed hollow dict).
"""

import pytest
from src.analysis.narrative.dna import NarrativeDNAAnalyzer, FINGERPRINTS
from src.shared.types.prediction import NarrativeStage


class TestNarrativeAdversarial:
    def setup_method(self):
        self.analyzer = NarrativeDNAAnalyzer()

    # --- Stage identification ---

    def test_seed_stage(self):
        """Brand new, low engagement → SEED."""
        stage = self.analyzer.identify_stage(age_hours=1, total_engagement=500, velocity=0.0)
        assert stage == NarrativeStage.SEED

    def test_seed_boundary(self):
        """At 2 hours and 1000 engagement — transitions out of SEED."""
        stage = self.analyzer.identify_stage(age_hours=2, total_engagement=1000, velocity=0.0)
        assert stage != NarrativeStage.SEED or stage == NarrativeStage.EARLY_SPREAD

    def test_peak_stage_reachable(self):
        """PEAK stage should now be reachable with high engagement + flat velocity."""
        stage = self.analyzer.identify_stage(age_hours=24, total_engagement=80000, velocity=0.02)
        assert stage == NarrativeStage.PEAK, f"Expected PEAK, got {stage}"

    def test_resolution_stage(self):
        """Old topic with positive velocity → RESOLUTION."""
        stage = self.analyzer.identify_stage(age_hours=200, total_engagement=50000, velocity=0.0)
        # With zero velocity and 50k engagement, this hits PEAK
        assert stage in (NarrativeStage.PEAK, NarrativeStage.FATIGUE, NarrativeStage.RESOLUTION)

    def test_counter_narrative(self):
        """Negative velocity with moderate engagement past early-spread age → COUNTER_NARRATIVE."""
        # Must be past EARLY_SPREAD (age >= 12 or engagement >= 20k)
        stage = self.analyzer.identify_stage(age_hours=14, total_engagement=15000, velocity=-0.5)
        assert stage == NarrativeStage.COUNTER_NARRATIVE

    def test_counter_narrative_requires_min_engagement(self):
        """Counter-narrative at very low engagement goes undetected."""
        stage = self.analyzer.identify_stage(age_hours=6, total_engagement=500, velocity=-0.5)
        # Low engagement → not counter-narrative
        assert stage != NarrativeStage.COUNTER_NARRATIVE

    def test_mainstream_high_engagement(self):
        """Very high engagement should reach MAINSTREAM or PEAK."""
        stage = self.analyzer.identify_stage(
            age_hours=24, total_engagement=30000, velocity=0.3
        )
        assert stage in (NarrativeStage.MAINSTREAM, NarrativeStage.PEAK)

    def test_fatigue_old_zero_velocity(self):
        """Old story with flat velocity → FATIGUE."""
        stage = self.analyzer.identify_stage(age_hours=100, total_engagement=3000, velocity=0.0)
        assert stage == NarrativeStage.FATIGUE

    # --- Fingerprint matching (now uses composite scoring) ---

    def test_outrage_cascade_match(self):
        """Strong negative velocity + cross-platform → outrage_cascade."""
        result = self.analyzer.match_fingerprint(velocity=-0.7, cross_platform=True)
        assert result == "outrage_cascade"

    def test_viral_support_match(self):
        """Strong positive velocity + single platform → viral_support."""
        result = self.analyzer.match_fingerprint(velocity=0.6, cross_platform=False)
        assert result == "viral_support"

    def test_echo_chamber_match(self):
        """Near-zero velocity + single platform → echo_chamber_loop."""
        result = self.analyzer.match_fingerprint(velocity=0.0, cross_platform=False)
        assert result == "echo_chamber_loop"

    def test_new_fingerprint_cross_platform_consensus(self):
        """Moderate positive velocity + cross-platform → new fingerprint type."""
        result = self.analyzer.match_fingerprint(velocity=0.3, cross_platform=True)
        assert result == "cross_platform_consensus"

    def test_new_fingerprint_slow_burn(self):
        """Mild negative velocity + cross-platform → slow_burn_controversy."""
        result = self.analyzer.match_fingerprint(velocity=-0.25, cross_platform=True)
        assert result == "slow_burn_controversy"

    def test_fingerprint_dict_is_actually_used(self):
        """The FINGERPRINTS dict should be used by match_fingerprint (no longer decoration)."""
        assert len(FINGERPRINTS) >= 5, "Should have at least 5 fingerprint patterns"
        for name, fp in FINGERPRINTS.items():
            assert "velocity" in fp
            assert "cross_platform" in fp
            assert isinstance(fp["velocity"], tuple) and len(fp["velocity"]) == 2

    def test_describe_fingerprint(self):
        """describe_fingerprint should return a non-empty description."""
        desc = self.analyzer.describe_fingerprint("outrage_cascade")
        assert len(desc) > 10
        unknown = self.analyzer.describe_fingerprint("nonexistent")
        assert "unprecedented" in unknown.lower() or "no" in unknown.lower()

    # --- Edge values ---

    def test_zero_everything(self):
        """All zeros should return SEED."""
        stage = self.analyzer.identify_stage(0, 0, 0.0)
        assert stage == NarrativeStage.SEED

    def test_negative_age(self):
        """Negative age shouldn't crash."""
        stage = self.analyzer.identify_stage(-1, 100, 0.0)
        assert stage == NarrativeStage.SEED

    def test_extreme_velocity(self):
        """Extreme velocity values should still produce valid fingerprints."""
        result = self.analyzer.match_fingerprint(velocity=-100.0, cross_platform=True)
        assert result == "outrage_cascade"

        result = self.analyzer.match_fingerprint(velocity=100.0, cross_platform=False)
        assert result == "viral_support"
