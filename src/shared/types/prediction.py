"""
Prediction type definitions shared across learning and output layers.
LOCK REQUIRED to edit this file — see .collab/RULES.md Rule 3.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class PredictionStatus(str, Enum):
    """Lifecycle of a prediction."""
    DRAFT = "draft"
    ACTIVE = "active"          # prediction is live, waiting for outcome
    VALIDATED_CORRECT = "validated_correct"
    VALIDATED_WRONG = "validated_wrong"
    PARTIALLY_CORRECT = "partially_correct"
    EXPIRED = "expired"         # outcome window passed, no validation possible


class ConfidenceLevel(str, Enum):
    """Human-readable confidence tiers."""
    VERY_LOW = "very_low"       # < 20%
    LOW = "low"                 # 20-40%
    MODERATE = "moderate"       # 40-60%
    HIGH = "high"               # 60-80%
    VERY_HIGH = "very_high"     # > 80%


class NarrativeStage(str, Enum):
    """Stage of a narrative's lifecycle."""
    SEED = "seed"               # initial event
    EARLY_SPREAD = "early_spread"  # influencers pick up
    COUNTER_NARRATIVE = "counter_narrative"  # opposition forms
    MAINSTREAM = "mainstream"   # media coverage
    PEAK = "peak"               # maximum saturation
    FATIGUE = "fatigue"         # people lose interest
    RESOLUTION = "resolution"   # story concludes or shifts


@dataclass
class Prediction:
    """A single prediction with confidence and tracking."""
    prediction_id: str
    topic: str
    prediction_text: str
    confidence: float  # 0.0 - 1.0
    predicted_at: datetime = field(default_factory=datetime.now)
    predicted_timeframe_hours: int = 72  # when this should happen

    # Source data
    source_signals_count: int = 0
    source_platforms: List[str] = field(default_factory=list)
    simulation_rounds: int = 0

    # Multi-agent debate scores
    bull_score: float = 0.0   # optimistic argument strength
    bear_score: float = 0.0   # pessimistic argument strength
    debate_consensus: float = 0.5  # 0 = total disagreement, 1 = unanimous

    # Validation
    status: PredictionStatus = PredictionStatus.DRAFT
    actual_outcome: Optional[str] = None
    validated_at: Optional[datetime] = None
    accuracy_score: Optional[float] = None  # 0-1 after validation

    # Narrative tracking
    narrative_stage: NarrativeStage = NarrativeStage.SEED

    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif self.confidence < 0.4:
            return ConfidenceLevel.LOW
        elif self.confidence < 0.6:
            return ConfidenceLevel.MODERATE
        elif self.confidence < 0.8:
            return ConfidenceLevel.HIGH
        return ConfidenceLevel.VERY_HIGH


@dataclass
class PredictionReport:
    """Full report combining multiple predictions."""
    report_id: str
    topic: str
    generated_at: datetime = field(default_factory=datetime.now)
    predictions: List[Prediction] = field(default_factory=list)
    executive_summary: str = ""
    sources_cited: List[Dict[str, str]] = field(default_factory=list)
    narrative_analysis: str = ""
    risk_assessment: str = ""
    confidence_calibration_note: str = ""

    @property
    def avg_confidence(self) -> float:
        if not self.predictions:
            return 0.0
        return sum(p.confidence for p in self.predictions) / len(self.predictions)
