from src.shared.types.prediction import NarrativeStage

class NarrativeDNAAnalyzer:
    def __init__(self):
        # Fingerprints match specific platform spread and emotional velocity metrics
        self.historical_fingerprints = {
            "outrage_cascade": {"velocity": -0.6, "cross_platform": True, "typical_stage": NarrativeStage.EARLY_SPREAD},
            "viral_support": {"velocity": 0.5, "cross_platform": False, "typical_stage": NarrativeStage.SEED},
            "echo_chamber_loop": {"velocity": 0.0, "cross_platform": False, "typical_stage": NarrativeStage.PEAK}
        }

    def identify_stage(self, age_hours: int, total_engagement: int, velocity: float) -> NarrativeStage:
        """
        Determines what stage a narrative is in based on time, engagement, and emotional velocity.
        """
        if age_hours < 2 and total_engagement < 1000:
            return NarrativeStage.SEED
        elif age_hours < 12 and velocity != 0 and total_engagement > 5000:
            return NarrativeStage.EARLY_SPREAD
        elif velocity < -0.3 and total_engagement > 20000:
            return NarrativeStage.COUNTER_NARRATIVE
        elif total_engagement > 100000:
            return NarrativeStage.MAINSTREAM
        elif age_hours > 72 and abs(velocity) < 0.1:
            return NarrativeStage.FATIGUE
        
        return NarrativeStage.EARLY_SPREAD

    def match_fingerprint(self, velocity: float, cross_platform: bool) -> str:
        """
        Matches a new story's metrics against historical narrative fingerprints.
        """
        if velocity <= -0.4 and cross_platform:
            return "outrage_cascade"
        elif velocity >= 0.4 and not cross_platform:
            return "viral_support"
        elif abs(velocity) < 0.2 and not cross_platform:
            return "echo_chamber_loop"
            
        return "unprecedented_pattern"
