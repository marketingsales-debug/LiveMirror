"""
Calibration Engine — connects simulation predictions to real outcomes.
Owner: Claude

The self-improving loop:
1. Run simulation → generate predictions
2. Wait for real data to come in
3. Compare predictions vs reality
4. Adjust agent behavioral fingerprints
5. Update confidence calibration curve
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from ...shared.types import AgentPersona
from ..engine.runner import SimulationState


@dataclass
class CalibrationAdjustment:
    """A single fingerprint adjustment derived from validation."""
    agent_id: int
    field: str          # which fingerprint field to adjust
    old_value: float
    new_value: float
    reason: str


@dataclass
class CalibrationReport:
    """Full report from a calibration cycle."""
    simulation_id: str
    accuracy: float
    adjustments: List[CalibrationAdjustment] = field(default_factory=list)
    confidence_offset: float = 0.0   # how much to shift future confidence scores
    calibrated_at: datetime = field(default_factory=datetime.now)
    diagnosis: str = ""


class CalibrationEngine:
    """
    Validates simulation predictions against real outcomes and adjusts
    agent behavioral fingerprints to improve future simulations.

    Design:
    - Accuracy 0.7+ → minor tune-ups only
    - Accuracy 0.3-0.7 → moderate fingerprint adjustments
    - Accuracy < 0.3 → aggressive reset toward neutral fingerprints
    - Confidence calibration uses EMA offset so the system learns
      whether it's systematically over or under-confident
    """

    # EMA coefficient for confidence offset updates
    CONFIDENCE_EMA = 0.2

    def __init__(self):
        self._history: List[CalibrationReport] = []
        self._confidence_offset: float = 0.0  # running EMA offset

    def calibrate(
        self,
        state: SimulationState,
        actual_outcome_sentiment: float,
        accuracy: float,
    ) -> CalibrationReport:
        """
        Compare simulation results against real outcome and adjust agents.

        Args:
            state:                     Completed simulation state
            actual_outcome_sentiment:  Real-world measured sentiment (-1 to 1)
            accuracy:                  How accurate the simulation was (0–1)

        Returns:
            CalibrationReport with adjustments applied
        """
        adjustments: List[CalibrationAdjustment] = []

        # Compute prediction error
        simulated_sentiment = state.topic_sentiment
        error = actual_outcome_sentiment - simulated_sentiment

        # Determine calibration severity
        if accuracy >= 0.7:
            severity = "minor"
        elif accuracy >= 0.3:
            severity = "moderate"
        else:
            severity = "aggressive"

        # Derive adjustments per agent
        for agent in state.agents:
            agent_adjustments = self._adjust_agent(
                agent, state, error, severity
            )
            adjustments.extend(agent_adjustments)

        # Update confidence calibration curve
        # If we were too confident (high confidence, low accuracy) → push offset down
        # If we were under-confident → push offset up
        avg_confidence = self._avg_prediction_confidence(state)
        expected_accuracy = avg_confidence  # calibrated system: confidence == accuracy
        confidence_error = accuracy - expected_accuracy
        self._confidence_offset = (
            self._confidence_offset * (1.0 - self.CONFIDENCE_EMA)
            + confidence_error * self.CONFIDENCE_EMA
        )

        diagnosis = self._diagnose(accuracy, error, severity, state)

        report = CalibrationReport(
            simulation_id=state.simulation_id,
            accuracy=accuracy,
            adjustments=adjustments,
            confidence_offset=self._confidence_offset,
            diagnosis=diagnosis,
        )

        self._history.append(report)
        return report

    def apply_confidence_correction(self, raw_confidence: float) -> float:
        """
        Adjust a raw confidence score using the learned calibration offset.
        Keeps score in [0.05, 0.95].
        """
        corrected = raw_confidence + self._confidence_offset
        return max(0.05, min(0.95, corrected))

    @property
    def calibration_history(self) -> List[CalibrationReport]:
        return list(self._history)

    @property
    def overall_accuracy(self) -> Optional[float]:
        if not self._history:
            return None
        return sum(r.accuracy for r in self._history) / len(self._history)

    @property
    def confidence_offset(self) -> float:
        return self._confidence_offset

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _adjust_agent(
        self,
        agent: AgentPersona,
        state: SimulationState,
        error: float,
        severity: str,
    ) -> List[CalibrationAdjustment]:
        """Compute fingerprint adjustments for one agent."""
        adjustments = []
        fp = agent.fingerprint

        # Count this agent's actions in the simulation
        agent_actions = [a for a in state.actions if a.agent_id == agent.agent_id]
        belief_shifts = len(agent.belief_history)
        rounds = max(state.total_rounds, 1)

        # --- Persuadability adjustment ---
        # Too many belief shifts → agent was too easily swayed → reduce persuadability
        shifts_per_round = belief_shifts / rounds
        if shifts_per_round > 0.5 and severity in ("moderate", "aggressive"):
            old = fp.persuadability
            delta = -0.05 if severity == "moderate" else -0.15
            new = max(0.05, old + delta)
            fp.persuadability = new
            adjustments.append(CalibrationAdjustment(
                agent_id=agent.agent_id,
                field="persuadability",
                old_value=old,
                new_value=new,
                reason=f"Too many belief shifts ({shifts_per_round:.2f}/round)",
            ))

        # --- Activity level adjustment ---
        # Too few actions → agent was less active than real world → increase activity
        actions_per_round = len(agent_actions) / rounds
        expected_activity = agent.activity_level
        if actions_per_round < expected_activity * 0.5 and severity != "minor":
            old = agent.activity_level
            new = min(1.0, old * 1.1)
            agent.activity_level = new
            adjustments.append(CalibrationAdjustment(
                agent_id=agent.agent_id,
                field="activity_level",
                old_value=old,
                new_value=new,
                reason=f"Under-active ({actions_per_round:.2f} actions/round vs {expected_activity:.2f} expected)",
            ))

        # --- Echo chamber adjustment ---
        # If simulation accuracy is low and echo chamber is high → echo chamber may be
        # isolating agents from real-world signal → reduce it
        if accuracy_below_threshold := (severity == "aggressive"):
            if fp.echo_chamber_score > 0.6:
                old = fp.echo_chamber_score
                new = max(0.3, old - 0.1)
                fp.echo_chamber_score = new
                adjustments.append(CalibrationAdjustment(
                    agent_id=agent.agent_id,
                    field="echo_chamber_score",
                    old_value=old,
                    new_value=new,
                    reason="High echo chamber may be hurting accuracy",
                ))

        # Update calibration timestamp
        fp.last_calibrated = datetime.now()
        fp.data_source = "calibrated"

        return adjustments

    def _avg_prediction_confidence(self, state: SimulationState) -> float:
        """Average confidence of predictions from this simulation."""
        if not state.predictions:
            return 0.5  # default neutral if no predictions
        return sum(p.confidence for p in state.predictions) / len(state.predictions)

    def _diagnose(
        self,
        accuracy: float,
        error: float,
        severity: str,
        state: SimulationState,
    ) -> str:
        """Generate a human-readable diagnosis of why the simulation was accurate or not."""
        parts = []

        if accuracy >= 0.7:
            parts.append(f"Good prediction accuracy ({accuracy:.0%}).")
        elif accuracy >= 0.4:
            parts.append(f"Moderate accuracy ({accuracy:.0%}) — room for improvement.")
        else:
            parts.append(f"Poor accuracy ({accuracy:.0%}) — significant recalibration needed.")

        direction = "underestimated" if error > 0 else "overestimated"
        if abs(error) > 0.1:
            parts.append(
                f"Simulation {direction} real-world sentiment by {abs(error):.2f}."
            )

        if state.round_summaries:
            avg_shifts = sum(r.belief_shifts for r in state.round_summaries) / len(state.round_summaries)
            if avg_shifts > 5:
                parts.append("High belief volatility detected — agents may be over-persuadable.")
            elif avg_shifts < 1:
                parts.append("Low belief dynamics — agents may be too rigid.")

        parts.append(f"Severity: {severity}. Confidence offset adjusted to {self._confidence_offset:+.3f}.")

        return " ".join(parts)
