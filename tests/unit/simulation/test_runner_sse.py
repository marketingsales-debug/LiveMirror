"""Unit tests for SimulationRunner SSE emission."""

import pytest
from unittest.mock import AsyncMock, patch
from src.simulation.engine.runner import SimulationRunner, SimulationState
from src.simulation.agents.factory import AgentFactory
from src.shared.types import AgentRole, Stance

@pytest.mark.asyncio
async def test_simulation_runner_emits_detailed_sse():
    """Verify that SimulationRunner.run() emits trust_network and belief_profile."""
    # 1. Setup agents
    factory = AgentFactory(seed=42)
    agents = [
        factory.create_synthetic(role=AgentRole.INFLUENCER, stance=Stance.SUPPORTIVE, name="Alpha", sentiment_bias=0.8),
        factory.create_synthetic(role=AgentRole.INDIVIDUAL, stance=Stance.OPPOSING, name="Beta", sentiment_bias=-0.7),
    ]
    # Set up a trust link
    agents[0].trust_network[agents[1].agent_id] = 0.9

    runner = SimulationRunner(seed=42)
    state = runner.create_simulation(topic="AI Regulation", agents=agents, total_rounds=1)

    # 2. Mock the SSE emission function
    with patch("backend.app.api.stream.emit_simulation_round", new_callable=AsyncMock) as mock_emit:
        # 3. Run one round
        await runner.run(state.simulation_id, emit_sse=True)

        # 4. Verify emission
        assert mock_emit.called
        args, kwargs = mock_emit.call_args
        
        # Check expected fields in kwargs (based on my recent changes)
        assert "trust_network" in kwargs
        assert "belief_profile" in kwargs
        
        trust_net = kwargs["trust_network"]
        assert "nodes" in trust_net
        assert "links" in trust_net
        assert len(trust_net["nodes"]) == 2
        assert any(link["trust"] == 0.9 for link in trust_net["links"])

        belief_profile = kwargs["belief_profile"]
        assert agents[0].agent_id in belief_profile
        assert agents[1].agent_id in belief_profile
        # Bias might have shifted slightly due to influence, but should exist
        assert isinstance(belief_profile[agents[0].agent_id], float)

if __name__ == "__main__":
    pytest.main([__file__])
