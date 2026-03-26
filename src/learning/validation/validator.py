"""
Prediction Validator — the self-improving loop.
Owner: Claude

This is the killer feature. It:
1. Tracks all predictions
2. Compares them against real outcomes
3. Diagnoses why predictions were wrong
4. Adjusts confidence calibration
5. Updates behavioral fingerprints
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from ...shared.types import Prediction, PredictionStatus


@dataclass
class ValidationResult:
    """Result of validating a prediction against reality."""
    prediction_id: str
    accuracy_score: float  # 0-1
    diagnosis: str  # why it was right/wrong
    failure_category: Optional[str] = None  # "bad_data", "wrong_model", "black_swan", etc.
    suggested_adjustments: Dict[str, float] = field(default_factory=dict)


class PredictionValidator:
    """
    Validates predictions against real outcomes.
    Tracks accuracy over time for confidence calibration.
    """

    def __init__(self):
        self._predictions: Dict[str, Prediction] = {}
        self._validations: List[ValidationResult] = []
        self._accuracy_history: List[float] = []

    def register_prediction(self, prediction: Prediction) -> None:
        """Register a new prediction for tracking."""
        self._predictions[prediction.prediction_id] = prediction

    def validate(
        self,
        prediction_id: str,
        actual_outcome: str,
        accuracy_score: float,
    ) -> ValidationResult:
        """
        Validate a prediction against what actually happened.

        Args:
            prediction_id: The prediction to validate
            actual_outcome: What actually happened
            accuracy_score: How accurate the prediction was (0-1)

        Returns:
            ValidationResult with diagnosis
        """
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            raise ValueError(f"Prediction not found: {prediction_id}")

        # Update prediction status
        prediction.actual_outcome = actual_outcome
        prediction.accuracy_score = accuracy_score
        prediction.validated_at = datetime.now()

        if accuracy_score >= 0.7:
            prediction.status = PredictionStatus.VALIDATED_CORRECT
        elif accuracy_score >= 0.3:
            prediction.status = PredictionStatus.PARTIALLY_CORRECT
        else:
            prediction.status = PredictionStatus.VALIDATED_WRONG

        # Diagnose
        diagnosis = self._diagnose(prediction, actual_outcome, accuracy_score)
        result = ValidationResult(
            prediction_id=prediction_id,
            accuracy_score=accuracy_score,
            diagnosis=diagnosis,
        )

        self._validations.append(result)
        self._accuracy_history.append(accuracy_score)

        return result

    def _diagnose(
        self,
        prediction: Prediction,
        actual_outcome: str,
        accuracy: float,
    ) -> str:
        """Diagnose why a prediction was right or wrong."""
        if accuracy >= 0.7:
            return "Prediction was accurate. Model performed well."

        # TODO: implement detailed diagnosis
        # - Check if source data was insufficient
        # - Check if simulation parameters were off
        # - Check if it was a genuinely unpredictable event
        return f"Prediction accuracy: {accuracy:.0%}. Needs investigation."

    @property
    def overall_accuracy(self) -> Optional[float]:
        """Average accuracy across all validated predictions."""
        if not self._accuracy_history:
            return None
        return sum(self._accuracy_history) / len(self._accuracy_history)

    @property
    def calibration_score(self) -> Optional[float]:
        """
        How well-calibrated are confidence scores?
        Perfect calibration: when we say 80% confident, we're right 80% of the time.
        """
        if len(self._validations) < 10:
            return None  # not enough data
        # TODO: implement proper calibration calculation
        return self.overall_accuracy
