"""
Multi-Agent Debate System — agents form bull/bear positions to generate predictions.
Owner: Claude

How it works:
1. Take a completed simulation's agent population
2. Split agents into BULL (supportive) and BEAR (opposing) camps based on stance
3. Each camp builds arguments from their behavioral evidence
4. Score argument strength based on agent influence, trust, and conviction
5. Compute consensus — how much agreement exists across all agents
6. Generate a final Prediction with confidence calibrated by debate outcome
"""

from typing import List
import uuid

from ..shared.types import (
    AgentPersona, Prediction, PredictionStatus, NarrativeStage,
    Stance, AgentRole,
)
from ..simulation.engine.runner import SimulationState


class DebateArgument:
    """A single argument from one agent in the debate."""

    __slots__ = ("agent_id", "agent_name", "role", "stance", "conviction",
                 "influence", "evidence_count", "trust_backing")

    def __init__(
        self,
        agent_id: int,
        agent_name: str,
        role: AgentRole,
        stance: Stance,
        conviction: float,
        influence: float,
        evidence_count: int,
        trust_backing: float,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.role = role
        self.stance = stance
        self.conviction = conviction
        self.influence = influence
        self.evidence_count = evidence_count
        self.trust_backing = trust_backing

    @property
    def strength(self) -> float:
        """Argument strength = influence × conviction × trust backing."""
        return self.influence * self.conviction * (0.5 + self.trust_backing * 0.5)


class DebateResult:
    """Outcome of a bull vs bear debate."""

    def __init__(
        self,
        bull_arguments: List[DebateArgument],
        bear_arguments: List[DebateArgument],
        neutral_count: int,
    ):
        self.bull_arguments = bull_arguments
        self.bear_arguments = bear_arguments
        self.neutral_count = neutral_count

    @property
    def bull_score(self) -> float:
        """Total strength of bullish arguments (0+)."""
        if not self.bull_arguments:
            return 0.0
        return sum(a.strength for a in self.bull_arguments)

    @property
    def bear_score(self) -> float:
        """Total strength of bearish arguments (0+)."""
        if not self.bear_arguments:
            return 0.0
        return sum(a.strength for a in self.bear_arguments)

    @property
    def consensus(self) -> float:
        """
        How much agreement exists (0 = total split, 1 = unanimous).
        Computed as the ratio of the dominant side to total strength.
        """
        total = self.bull_score + self.bear_score
        if total == 0:
            return 0.5
        dominant = max(self.bull_score, self.bear_score)
        return dominant / total

    @property
    def direction(self) -> str:
        """Which side won: 'bull', 'bear', or 'split'."""
        diff = self.bull_score - self.bear_score
        if abs(diff) < 0.1 * max(self.bull_score, self.bear_score, 1.0):
            return "split"
        return "bull" if diff > 0 else "bear"

    @property
    def confidence(self) -> float:
        """
        Raw confidence from debate outcome (0.0–1.0).
        High consensus + strong arguments = high confidence.
        Low consensus or weak arguments = low confidence.
        """
        total = self.bull_score + self.bear_score
        if total == 0:
            return 0.1

        # Consensus contribution (0–0.5)
        consensus_part = self.consensus * 0.5

        # Strength contribution — how strong are the arguments overall (0–0.5)
        agent_count = len(self.bull_arguments) + len(self.bear_arguments) + self.neutral_count
        avg_strength = total / max(agent_count, 1)
        # Normalize: avg_strength of 2.0 → 0.5 contribution
        strength_part = min(0.5, avg_strength / 4.0)

        return min(0.95, max(0.05, consensus_part + strength_part))


class DebateEngine:
    """
    Runs multi-agent debates on completed simulations to produce predictions.

    Usage:
        engine = DebateEngine()
        result = engine.debate(simulation_state)
        prediction = engine.to_prediction(result, topic="AI regulation")
    """

    def debate(self, state: SimulationState) -> DebateResult:
        """
        Run a bull vs bear debate across all agents in the simulation.

        Agents are classified by their final stance/sentiment:
        - Positive sentiment → BULL
        - Negative sentiment → BEAR
        - Near-zero sentiment → NEUTRAL (counted but don't argue)
        """
        bull_args: List[DebateArgument] = []
        bear_args: List[DebateArgument] = []
        neutral_count = 0

        for agent in state.agents:
            # Conviction = how far the agent is from neutral
            conviction = abs(agent.sentiment_bias)

            # Trust backing = average trust from other agents toward this one
            trust_backing = self._compute_trust_backing(agent, state.agents)

            # Evidence = how many actions this agent took (more active = more evidence)
            evidence_count = sum(
                1 for a in state.actions if a.agent_id == agent.agent_id
            )

            if agent.sentiment_bias > 0.1:
                bull_args.append(DebateArgument(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    role=agent.role,
                    stance=Stance.SUPPORTIVE,
                    conviction=conviction,
                    influence=agent.influence_weight,
                    evidence_count=evidence_count,
                    trust_backing=trust_backing,
                ))
            elif agent.sentiment_bias < -0.1:
                bear_args.append(DebateArgument(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    role=agent.role,
                    stance=Stance.OPPOSING,
                    conviction=conviction,
                    influence=agent.influence_weight,
                    evidence_count=evidence_count,
                    trust_backing=trust_backing,
                ))
            else:
                neutral_count += 1

        return DebateResult(bull_args, bear_args, neutral_count)

    def to_prediction(
        self,
        result: DebateResult,
        topic: str,
        state: SimulationState,
        narrative_stage: NarrativeStage = NarrativeStage.SEED,
        confidence_correction: float = 0.0,
    ) -> Prediction:
        """
        Convert a debate result into a Prediction.

        Args:
            result:                Debate outcome
            topic:                 Topic being predicted
            state:                 Simulation state for metadata
            narrative_stage:       Current narrative stage from analysis
            confidence_correction: Calibration offset from CalibrationEngine
        """
        direction = result.direction
        confidence = min(0.95, max(0.05, result.confidence + confidence_correction))

        if direction == "bull":
            text = f"Positive trajectory expected for '{topic}' — bullish sentiment dominates with {result.consensus:.0%} consensus."
        elif direction == "bear":
            text = f"Negative trajectory expected for '{topic}' — bearish sentiment dominates with {result.consensus:.0%} consensus."
        else:
            text = f"Mixed signals for '{topic}' — agents are split with no clear consensus ({result.consensus:.0%})."

        return Prediction(
            prediction_id=f"pred_{uuid.uuid4().hex[:12]}",
            topic=topic,
            prediction_text=text,
            confidence=confidence,
            source_signals_count=len(state.actions),
            source_platforms=list({a.platform for a in state.actions}),
            simulation_rounds=state.total_rounds,
            bull_score=round(result.bull_score, 3),
            bear_score=round(result.bear_score, 3),
            debate_consensus=round(result.consensus, 3),
            status=PredictionStatus.ACTIVE,
            narrative_stage=narrative_stage,
        )

    def _compute_trust_backing(
        self, agent: AgentPersona, all_agents: List[AgentPersona]
    ) -> float:
        """Average trust other agents have toward this agent."""
        trust_scores = []
        for other in all_agents:
            if other.agent_id == agent.agent_id:
                continue
            trust = other.trust_network.get(agent.agent_id)
            if trust is not None:
                trust_scores.append(trust)
        if not trust_scores:
            return 0.5
        return sum(trust_scores) / len(trust_scores)
