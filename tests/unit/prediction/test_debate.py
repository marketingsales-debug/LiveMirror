"""
Tests for the multi-agent debate system.
Owner: Claude
"""

import pytest
from src.prediction.debate import DebateEngine, DebateArgument, DebateResult
from src.simulation.engine.runner import SimulationRunner, SimulationAction
from src.simulation.agents.factory import AgentFactory
from src.shared.types import AgentPersona, AgentRole, Stance, BehavioralFingerprint


def _make_agent(
    agent_id: int,
    name: str = "TestAgent",
    sentiment_bias: float = 0.0,
    influence_weight: float = 1.0,
    role: AgentRole = AgentRole.INDIVIDUAL,
) -> AgentPersona:
    return AgentPersona(
        agent_id=agent_id,
        name=name,
        role=role,
        entity_type=role.value,
        sentiment_bias=sentiment_bias,
        influence_weight=influence_weight,
        stance=Stance.SUPPORTIVE if sentiment_bias > 0.1 else (
            Stance.OPPOSING if sentiment_bias < -0.1 else Stance.NEUTRAL
        ),
        fingerprint=BehavioralFingerprint(),
    )


class TestDebateEngine:
    """Test multi-agent debate logic."""

    def setup_method(self):
        self.engine = DebateEngine()
        self.runner = SimulationRunner(seed=42)

    def test_unanimous_bull_debate(self):
        """All bullish agents → high consensus, bull direction."""
        agents = [_make_agent(i, f"Bull_{i}", sentiment_bias=0.5) for i in range(10)]
        state = self.runner.create_simulation("test", agents, total_rounds=1)
        state.actions = [
            SimulationAction(0, "t", "test", i, f"Bull_{i}", "CREATE_POST")
            for i in range(10)
        ]

        result = self.engine.debate(state)
        assert result.direction == "bull"
        assert result.consensus > 0.9
        assert result.bull_score > 0
        assert result.bear_score == 0.0

    def test_unanimous_bear_debate(self):
        """All bearish agents → high consensus, bear direction."""
        agents = [_make_agent(i, f"Bear_{i}", sentiment_bias=-0.5) for i in range(10)]
        state = self.runner.create_simulation("test", agents, total_rounds=1)
        state.actions = []

        result = self.engine.debate(state)
        assert result.direction == "bear"
        assert result.consensus > 0.9

    def test_split_debate(self):
        """Equal bull and bear → split direction, low consensus."""
        agents = (
            [_make_agent(i, f"Bull_{i}", sentiment_bias=0.5, influence_weight=1.0) for i in range(5)]
            + [_make_agent(i + 5, f"Bear_{i}", sentiment_bias=-0.5, influence_weight=1.0) for i in range(5)]
        )
        state = self.runner.create_simulation("test", agents, total_rounds=1)
        state.actions = []

        result = self.engine.debate(state)
        assert result.consensus < 0.7

    def test_neutral_agents_excluded_from_arguments(self):
        """Agents near zero sentiment should be neutral, not bull or bear."""
        agents = [
            _make_agent(0, "Bull", sentiment_bias=0.5),
            _make_agent(1, "Bear", sentiment_bias=-0.5),
            _make_agent(2, "Neutral", sentiment_bias=0.05),
            _make_agent(3, "Neutral2", sentiment_bias=-0.05),
        ]
        state = self.runner.create_simulation("test", agents, total_rounds=1)
        state.actions = []

        result = self.engine.debate(state)
        assert len(result.bull_arguments) == 1
        assert len(result.bear_arguments) == 1
        assert result.neutral_count == 2

    def test_influencer_has_more_strength(self):
        """Influencers with high influence_weight should have stronger arguments."""
        agents = [
            _make_agent(0, "Regular", sentiment_bias=0.5, influence_weight=0.5),
            _make_agent(1, "Influencer", sentiment_bias=0.5, influence_weight=3.0, role=AgentRole.INFLUENCER),
        ]
        state = self.runner.create_simulation("test", agents, total_rounds=1)
        state.actions = []

        result = self.engine.debate(state)
        strengths = [a.strength for a in result.bull_arguments]
        # Influencer should have higher strength
        influencer_arg = next(a for a in result.bull_arguments if a.agent_name == "Influencer")
        regular_arg = next(a for a in result.bull_arguments if a.agent_name == "Regular")
        assert influencer_arg.strength > regular_arg.strength

    def test_to_prediction_bull(self):
        """Bull debate → positive prediction text with confidence."""
        agents = [_make_agent(i, f"Bull_{i}", sentiment_bias=0.6) for i in range(10)]
        state = self.runner.create_simulation("AI regulation", agents, total_rounds=72)
        state.actions = [
            SimulationAction(0, "t", "test", i, f"Bull_{i}", "CREATE_POST")
            for i in range(10)
        ]

        result = self.engine.debate(state)
        prediction = self.engine.to_prediction(result, "AI regulation", state)

        assert prediction.topic == "AI regulation"
        assert prediction.confidence > 0.3
        assert prediction.bull_score > 0
        assert "Positive" in prediction.prediction_text
        assert prediction.status.value == "active"

    def test_to_prediction_bear(self):
        """Bear debate → negative prediction text."""
        agents = [_make_agent(i, f"Bear_{i}", sentiment_bias=-0.6) for i in range(10)]
        state = self.runner.create_simulation("crypto crash", agents, total_rounds=72)
        state.actions = []

        result = self.engine.debate(state)
        prediction = self.engine.to_prediction(result, "crypto crash", state)

        assert "Negative" in prediction.prediction_text
        assert prediction.bear_score > 0

    def test_confidence_bounded(self):
        """Confidence should always be between 0.05 and 0.95."""
        # Empty simulation → low confidence
        state = self.runner.create_simulation("test", [], total_rounds=1)
        state.actions = []
        result = self.engine.debate(state)
        prediction = self.engine.to_prediction(result, "test", state)
        assert 0.05 <= prediction.confidence <= 0.95

    def test_debate_result_empty_agents(self):
        """Debate with no agents should not crash."""
        state = self.runner.create_simulation("test", [], total_rounds=1)
        state.actions = []
        result = self.engine.debate(state)
        assert result.bull_score == 0.0
        assert result.bear_score == 0.0
        assert result.consensus == 0.5
        assert result.direction == "split"

    def test_trust_backing_affects_strength(self):
        """Agents trusted by others should have higher argument strength."""
        agent_trusted = _make_agent(0, "Trusted", sentiment_bias=0.5)
        agent_normal = _make_agent(1, "Normal", sentiment_bias=0.5)
        # Agent 1 trusts agent 0 highly
        agent_normal.trust_network[0] = 0.9

        agents = [agent_trusted, agent_normal]
        state = self.runner.create_simulation("test", agents, total_rounds=1)
        state.actions = []

        result = self.engine.debate(state)
        trusted_arg = next(a for a in result.bull_arguments if a.agent_name == "Trusted")
        normal_arg = next(a for a in result.bull_arguments if a.agent_name == "Normal")
        assert trusted_arg.trust_backing > normal_arg.trust_backing
