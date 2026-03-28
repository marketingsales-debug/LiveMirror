"""
Tests for the learning loop (self-improving feedback cycle).
Owner: Claude
"""

import pytest
from src.learning.loop import LearningLoop
from src.learning.validation.validator import PredictionValidator
from src.simulation.calibration.calibrator import CalibrationEngine
from src.simulation.engine.runner import SimulationRunner
from src.simulation.agents.factory import AgentFactory
from src.shared.types import Prediction, PredictionStatus


def _make_prediction(pred_id: str = "pred_test", confidence: float = 0.7) -> Prediction:
    return Prediction(
        prediction_id=pred_id,
        topic="AI regulation",
        prediction_text="Positive trajectory expected",
        confidence=confidence,
    )


class TestLearningLoop:
    def setup_method(self):
        self.loop = LearningLoop()

    def test_register_and_validate(self):
        """Register a prediction and validate it."""
        pred = _make_prediction()
        self.loop.register_prediction(pred)

        result = self.loop.validate_and_calibrate(
            prediction_id="pred_test",
            actual_outcome="AI regulation passed with strong support",
            accuracy_score=0.8,
        )

        assert result["validation"].accuracy_score == 0.8
        assert result["validation"].diagnosis is not None
        assert result["learning_stats"]["total_validations"] == 1
        assert result["learning_stats"]["overall_accuracy"] == 0.8

    def test_validate_with_calibration(self):
        """Validate with simulation state triggers calibration."""
        runner = SimulationRunner(seed=42)
        factory = AgentFactory(seed=42)

        agents = [factory.create_synthetic(name=f"Agent_{i}") for i in range(10)]
        state = runner.create_simulation("AI regulation", agents, total_rounds=5)

        pred = _make_prediction()
        self.loop.register_prediction(pred)

        result = self.loop.validate_and_calibrate(
            prediction_id="pred_test",
            actual_outcome="Positive outcome",
            accuracy_score=0.6,
            simulation_state=state,
        )

        assert result["calibration"] is not None
        assert result["calibration"].accuracy == 0.6

    def test_confidence_correction_tracks(self):
        """Multiple validations adjust confidence offset."""
        for i in range(3):
            pred = _make_prediction(f"pred_{i}", confidence=0.8)
            self.loop.register_prediction(pred)
            self.loop.validate_and_calibrate(
                prediction_id=f"pred_{i}",
                actual_outcome="Bad outcome",
                accuracy_score=0.3,
            )

        # After multiple poor predictions at high confidence,
        # the offset should push down
        assert self.loop.stats["total_validations"] == 3
        assert self.loop.stats["overall_accuracy"] == 0.3

    def test_correct_confidence(self):
        """Confidence correction applies learned offset."""
        raw = 0.7
        corrected = self.loop.correct_confidence(raw)
        # No validations yet, offset is 0 → corrected ≈ raw
        assert 0.05 <= corrected <= 0.95

    def test_learning_history_recorded(self):
        """Each validation adds to learning history."""
        pred = _make_prediction()
        self.loop.register_prediction(pred)
        self.loop.validate_and_calibrate("pred_test", "outcome", 0.5)

        assert len(self.loop.learning_history) == 1
        assert self.loop.learning_history[0]["accuracy"] == 0.5

    def test_outcome_sentiment_estimation(self):
        """Outcome sentiment estimation for calibration."""
        pos = self.loop._estimate_outcome_sentiment("Great success and growth")
        neg = self.loop._estimate_outcome_sentiment("Total failure and collapse")
        neutral = self.loop._estimate_outcome_sentiment("The meeting happened")

        assert pos > 0
        assert neg < 0
        assert neutral == 0.0
