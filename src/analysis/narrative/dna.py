"""
NarrativeDNAAnalyzer — Identifies where a story is in its lifecycle and
matches it against historical narrative patterns.

Fixes applied per Claude's adversarial review:
  - PEAK stage was unreachable (threshold logic fixed)
  - Growth phase was misclassified as EARLY_SPREAD
  - Historical fingerprint dict is now actually used in match_fingerprint
"""

from src.shared.types.prediction import NarrativeStage


# ---------------------------------------------------------------------------
# Historical fingerprint database
# ---------------------------------------------------------------------------
FINGERPRINTS = {
    "outrage_cascade": {
        "velocity": (-1.0, -0.4),       # (min, max)
        "cross_platform": True,
        "typical_stage": NarrativeStage.COUNTER_NARRATIVE,
        "description": "Anger spreads rapidly across platforms — usually a PR crisis or controversial event.",
    },
    "viral_support": {
        "velocity": (0.4, 1.0),
        "cross_platform": False,
        "typical_stage": NarrativeStage.EARLY_SPREAD,
        "description": "Positive momentum building on a single platform before going cross-platform.",
    },
    "echo_chamber_loop": {
        "velocity": (-0.2, 0.2),
        "cross_platform": False,
        "typical_stage": NarrativeStage.PEAK,
        "description": "Community stuck in a self-reinforcing loop — growth has flatlined.",
    },
    "cross_platform_consensus": {
        "velocity": (0.2, 0.5),
        "cross_platform": True,
        "typical_stage": NarrativeStage.MAINSTREAM,
        "description": "Positive narrative reaching mainstream through multiple channels.",
    },
    "slow_burn_controversy": {
        "velocity": (-0.4, -0.1),
        "cross_platform": True,
        "typical_stage": NarrativeStage.FATIGUE,
        "description": "Mild but persistent negativity — simmering discontent without explosion.",
    },
}


class NarrativeDNAAnalyzer:
    """
    Identifies narrative lifecycle stage and matches patterns against
    historical fingerprints.
    """

    def identify_stage(
        self,
        age_hours: float,
        total_engagement: int,
        velocity: float,
    ) -> NarrativeStage:
        """
        Determine what stage a narrative is currently in.

        Args:
            age_hours:         Hours since the seed event.
            total_engagement:  Total reactions (likes + shares + comments).
            velocity:          Emotional velocity from ContagionTracker (-1 to 1).
        """
        # SEED — brand new, low engagement
        if age_hours < 2 and total_engagement < 1_000:
            return NarrativeStage.SEED

        # EARLY_SPREAD — picking up traction, moving fast
        if age_hours < 12 and total_engagement < 20_000:
            return NarrativeStage.EARLY_SPREAD

        # COUNTER_NARRATIVE — opposition forming with high velocity flip
        if velocity < -0.3 and 5_000 < total_engagement < 100_000:
            return NarrativeStage.COUNTER_NARRATIVE

        # PEAK — maximum saturation (fix: lowered threshold from 100k)
        if total_engagement >= 50_000 and abs(velocity) < 0.15:
            return NarrativeStage.PEAK

        # MAINSTREAM — cross-platform and high engagement but not yet plateau
        if total_engagement >= 20_000:
            return NarrativeStage.MAINSTREAM

        # FATIGUE — old story, velocity near-zero
        if age_hours > 72 and abs(velocity) < 0.1:
            return NarrativeStage.FATIGUE

        # RESOLUTION — story concludes (strong positive velocity at age)
        if age_hours > 48 and velocity > 0.2:
            return NarrativeStage.RESOLUTION

        return NarrativeStage.EARLY_SPREAD

    def match_fingerprint(self, velocity: float, cross_platform: bool) -> str:
        """
        Matches a story against historical fingerprints by scoring each one.
        Returns the name of the best matching fingerprint.
        """
        best_match = "unprecedented_pattern"
        best_score = -1.0

        for name, fp in FINGERPRINTS.items():
            vel_min, vel_max = fp["velocity"]
            cross_match = fp["cross_platform"] == cross_platform

            # Velocity match: 1.0 if inside range, partial credit for proximity
            if vel_min <= velocity <= vel_max:
                vel_score = 1.0
            else:
                dist = min(abs(velocity - vel_min), abs(velocity - vel_max))
                vel_score = max(0.0, 1.0 - dist)

            cross_score = 1.0 if cross_match else 0.0
            composite = vel_score * 0.7 + cross_score * 0.3

            if composite > best_score:
                best_score = composite
                best_match = name

        return best_match

    def describe_fingerprint(self, name: str) -> str:
        """Returns a human-readable description of a named fingerprint."""
        if name in FINGERPRINTS:
            return FINGERPRINTS[name]["description"]
        return "No historical match found — this narrative pattern may be unprecedented."
