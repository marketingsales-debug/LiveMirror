"""
Learning Loop — the self-improving feedback cycle.
Owner: Claude

Wires together:
1. PredictionValidator — tracks predictions against outcomes
2. CalibrationEngine — adjusts agent fingerprints
3. FineTuningLoop — updates fusion attention weights
4. Re-ingestion — pulls fresh data to compare predictions

This is the "brain" that makes LiveMirror get smarter over time.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..shared.types import Prediction, PredictionStatus
from ..simulation.calibration.calibrator import CalibrationEngine, CalibrationReport
from ..simulation.engine.runner import SimulationRunner, SimulationState
from .validation.validator import PredictionValidator, ValidationResult
from .fine_tune import FineTuningLoop, FineTuneConfig


class LearningLoop:
    """
    Self-improving feedback loop.

    Cycle:
    1. A prediction is made (registered)
    2. Time passes, real data comes in
    3. validate() compares prediction vs reality
    4. calibrate() adjusts agent fingerprints based on accuracy
    5. fine_tune() updates fusion attention weights (when threshold met)
    6. Next simulation uses adjusted fingerprints → better predictions

    The calibration engine uses EMA to track systematic over/under-confidence
    and adjusts future confidence scores accordingly.
    """

    def __init__(
        self,
        validator: Optional[PredictionValidator] = None,
        calibrator: Optional[CalibrationEngine] = None,
        fine_tuning_loop: Optional[FineTuningLoop] = None,
        fusion_pipeline=None,
    ):
        self.validator = validator or PredictionValidator()
        self.calibrator = calibrator or CalibrationEngine()
        self.fine_tuning = fine_tuning_loop or FineTuningLoop(
            fusion_pipeline=fusion_pipeline
        )
        self._learning_history: List[Dict[str, Any]] = []
        self._pending_signals: Dict[str, List[Dict[str, Any]]] = {}  # prediction_id -> signals

    def register_prediction(
        self, 
        prediction: Prediction,
        signals: Optional[List[Any]] = None,
    ) -> None:
        """
        Register a new prediction for tracking.
        
        Args:
            prediction: The prediction to track
            signals: Optional list of signals used for this prediction
        """
        self.validator.register_prediction(prediction)
        
        # Store signals for fine-tuning when validated
        if signals:
            self._pending_signals[prediction.prediction_id] = [
                {"content": s.signal.content, "platform": s.signal.platform.value}
                for s in signals[:20]  # Keep top 20 signals
            ]

    def validate_and_calibrate(
        self,
        prediction_id: str,
        actual_outcome: str,
        accuracy_score: float,
        simulation_state: Optional[SimulationState] = None,
        predicted_direction: Optional[str] = None,
        predicted_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Full learning cycle: validate prediction → calibrate agents → queue fine-tune.

        Args:
            prediction_id:     The prediction to validate
            actual_outcome:    What actually happened
            accuracy_score:    How accurate (0–1)
            simulation_state:  The simulation that generated this prediction
                               (needed for fingerprint adjustments)
            predicted_direction: Optional direction for fine-tuning
            predicted_confidence: Optional confidence for fine-tuning

        Returns:
            Dict with validation result, calibration report, and learning stats
        """
        # Step 1: Validate
        validation = self.validator.validate(
            prediction_id=prediction_id,
            actual_outcome=actual_outcome,
            accuracy_score=accuracy_score,
        )

        # Step 2: Calibrate (if we have the simulation state)
        calibration = None
        if simulation_state:
            # Compute actual sentiment from the outcome text
            actual_sentiment = self._estimate_outcome_sentiment(actual_outcome)

            calibration = self.calibrator.calibrate(
                state=simulation_state,
                actual_outcome_sentiment=actual_sentiment,
                accuracy=accuracy_score,
            )

        # Step 3: Add validated samples to fine-tuning queue
        fine_tune_result = None
        actual_direction = self._outcome_to_direction(actual_outcome)
        
        if prediction_id in self._pending_signals:
            signals = self._pending_signals.pop(prediction_id)
            for signal in signals:
                self.fine_tuning.add_validated_sample(
                    content=signal["content"],
                    actual_direction=actual_direction,
                    predicted_direction=predicted_direction or actual_direction,
                    predicted_confidence=predicted_confidence or accuracy_score,
                    platform=signal.get("platform"),
                )
        
        # Step 4: Maybe trigger fine-tuning
        fine_tune_result = self.fine_tuning.maybe_fine_tune()

        # Step 5: Record learning event
        event = {
            "timestamp": datetime.now().isoformat(),
            "prediction_id": prediction_id,
            "accuracy": accuracy_score,
            "validation_diagnosis": validation.diagnosis,
            "calibration_adjustments": (
                len(calibration.adjustments) if calibration else 0
            ),
            "confidence_offset": self.calibrator.confidence_offset,
            "overall_accuracy": self.validator.overall_accuracy,
            "fine_tune_triggered": fine_tune_result is not None,
        }
        self._learning_history.append(event)

        return {
            "validation": validation,
            "calibration": calibration,
            "fine_tune": fine_tune_result,
            "learning_stats": self.stats,
        }

    def correct_confidence(self, raw_confidence: float) -> float:
        """Apply learned calibration offset to a raw confidence score."""
        return self.calibrator.apply_confidence_correction(raw_confidence)

    @property
    def stats(self) -> Dict[str, Any]:
        """Current learning statistics."""
        return {
            "total_validations": len(self._learning_history),
            "overall_accuracy": self.validator.overall_accuracy,
            "confidence_offset": self.calibrator.confidence_offset,
            "calibration_history_count": len(self.calibrator.calibration_history),
            "calibration_score": self.validator.calibration_score,
            "fine_tune_pending_samples": self.fine_tuning.pending_sample_count(),
            "fine_tune_runs": self.fine_tuning.stats["total_tune_runs"],
        }

    @property
    def learning_history(self) -> List[Dict[str, Any]]:
        return list(self._learning_history)

    def _estimate_outcome_sentiment(self, outcome_text: str) -> float:
        """
        Quick sentiment estimate from outcome text.
        Used to compute prediction error for calibration.

        This is intentionally simple — the full sentiment analysis
        lives in Gemini's AnalysisPipeline.
        """
        positive_words = {
            "success", "growth", "positive", "increase", "gain", "rise",
            "improvement", "profit", "bullish", "rally", "surge", "good",
            "great", "excellent", "strong", "up", "higher", "better",
        }
        negative_words = {
            "failure", "decline", "negative", "decrease", "loss", "fall",
            "crash", "crisis", "bearish", "collapse", "bad", "poor",
            "weak", "down", "lower", "worse", "drop", "plunge",
        }

        words = set(outcome_text.lower().split())
        pos_count = len(words & positive_words)
        neg_count = len(words & negative_words)
        total = pos_count + neg_count

        if total == 0:
            return 0.0
        return (pos_count - neg_count) / total

    def _outcome_to_direction(self, outcome_text: str) -> str:
        """Convert outcome text to direction string."""
        sentiment = self._estimate_outcome_sentiment(outcome_text)
        if sentiment > 0.2:
            return "bullish"
        elif sentiment < -0.2:
            return "bearish"
        return "neutral"
