"""
Integration Adapter — bridges Claude's ingestion pipeline to Gemini's analysis layer.

Takes a ScoredSignal (produced by Claude's scorer) and runs it
through SentimentAnalyzer → EmotionalContagionTracker → NarrativeDNAAnalyzer
as a unified pipeline, returning a structured AnalysisResult.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.shared.types.platform import ScoredSignal, Platform
from src.shared.types.prediction import NarrativeStage
from src.analysis.sentiment.analyzer import SentimentAnalyzer
from src.analysis.emotional.contagion import EmotionalContagionTracker
from src.analysis.narrative.dna import NarrativeDNAAnalyzer


@dataclass
class AnalysisResult:
    """Unified output from the full analysis pipeline for a single signal."""
    signal_id: str
    platform: str

    # Sentiment
    sentiment_score: float = 0.0         # -1.0 to 1.0

    # Contagion
    emotional_velocity: float = 0.0      # rate of sentiment shift
    is_tipping_point: bool = False        # cascade imminent?

    # Narrative
    narrative_stage: NarrativeStage = NarrativeStage.SEED
    fingerprint: str = "unknown"

    analyzed_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class AnalysisPipeline:
    """
    Orchestrates the full Gemini analysis pipeline.

    Usage:
        pipeline = AnalysisPipeline()
        result = pipeline.process(scored_signal)
    """

    def __init__(
        self,
        tipping_threshold: float = 0.4,
        max_history: int = 10_000,
    ):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.contagion_tracker = EmotionalContagionTracker(
            tipping_point_threshold=tipping_threshold,
            max_history=max_history,
        )
        self.narrative_analyzer = NarrativeDNAAnalyzer()

    def process(
        self,
        signal: ScoredSignal,
        age_hours: float = 1.0,
        cross_platform: bool = False,
    ) -> AnalysisResult:
        """
        Runs a single ScoredSignal through the full analysis stack.

        Args:
            signal:        Scored signal from Claude's ingestion scorer.
            age_hours:     How long this story has been in circulation.
            cross_platform: Whether this signal appears on multiple platforms.
        """
        platform = signal.signal.platform
        content = signal.signal.content
        timestamp = signal.signal.timestamp or datetime.now(tz=timezone.utc)
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # --- 1. Sentiment --------------------------------------------------
        sentiment = self.sentiment_analyzer.analyze(content, platform)

        # --- 2. Contagion --------------------------------------------------
        signal_id = str(id(signal))
        self.contagion_tracker.record_sentiment(
            text_id=signal_id,
            platform=str(platform),
            sentiment_score=sentiment,
            timestamp=timestamp,
        )
        velocity = self.contagion_tracker.calculate_emotional_velocity()
        tipping = self.contagion_tracker.detect_tipping_point(velocity)

        # --- 3. Narrative --------------------------------------------------
        total_engagement = signal.signal.engagement_score()
        stage = self.narrative_analyzer.identify_stage(
            age_hours=age_hours,
            total_engagement=total_engagement,
            velocity=velocity,
        )
        fingerprint = self.narrative_analyzer.match_fingerprint(
            velocity=velocity,
            cross_platform=cross_platform,
        )

        return AnalysisResult(
            signal_id=signal_id,
            platform=str(platform),
            sentiment_score=sentiment,
            emotional_velocity=velocity,
            is_tipping_point=tipping,
            narrative_stage=stage,
            fingerprint=fingerprint,
        )

    def process_batch(self, signals: list, **kwargs) -> list:
        """Convenience wrapper to process a list of ScoredSignals."""
        return [self.process(s, **kwargs) for s in signals]
