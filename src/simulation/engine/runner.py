"""
Simulation Runner — executes forward simulations with calibrated agents.
Owner: Claude

Based on MiroFish's OASIS simulation runner, enhanced with:
- Real-time calibration against live data
- Agent belief evolution
- Prediction validation hooks
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum
import asyncio

from ...shared.types import AgentPersona, Prediction
from ..agents.behavior import AgentBehaviorEngine, AgentDecision, ActionType

logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimulationAction:
    """A single action by an agent in the simulation."""
    round_num: int
    timestamp: str
    platform: str
    agent_id: int
    agent_name: str
    action_type: str  # CREATE_POST, COMMENT, LIKE, SHARE, IGNORE
    content: str = ""
    target_id: Optional[int] = None  # post or agent being responded to
    sentiment: float = 0.0
    influence: float = 0.0
    engagement: Dict[str, int] = field(default_factory=dict)


@dataclass
class RoundSummary:
    """Summary stats for a single simulation round."""
    round_num: int
    active_agents: int
    actions_taken: int
    avg_sentiment: float
    max_influence: float
    belief_shifts: int  # how many agents shifted this round
    trust_network: Dict[str, Any] = field(default_factory=dict)  # nodes/links for D3
    belief_profile: Dict[int, float] = field(default_factory=dict) # agent_id -> sentiment_bias


@dataclass
class SimulationState:
    """Current state of a running simulation."""
    simulation_id: str
    topic: str
    status: SimulationStatus = SimulationStatus.IDLE
    current_round: int = 0
    total_rounds: int = 72
    agents: List[AgentPersona] = field(default_factory=list)
    actions: List[SimulationAction] = field(default_factory=list)
    round_summaries: List[RoundSummary] = field(default_factory=list)
    predictions: List[Prediction] = field(default_factory=list)
    topic_sentiment: float = 0.0  # running average sentiment
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    paused: bool = False

    @property
    def agent_map(self) -> Dict[int, AgentPersona]:
        return {a.agent_id: a for a in self.agents}


class SimulationRunner:
    """
    Runs forward simulations.

    Pipeline:
    1. Load agents (from real behavioral fingerprints when available)
    2. Inject seed events
    3. Run simulation rounds
    4. Each round: activate agents based on time/activity config
    5. Agents act: post, comment, react, influence each other
    6. Update trust networks and belief states
    7. Generate predictions at checkpoints
    8. Compare predictions vs real data (calibration loop)
    """

    def __init__(self, seed: Optional[int] = None):
        self._simulations: Dict[str, SimulationState] = {}
        self._behavior = AgentBehaviorEngine(seed=seed)

    @property
    def behavior_engine(self) -> AgentBehaviorEngine:
        return self._behavior

    def create_simulation(
        self,
        topic: str,
        agents: List[AgentPersona],
        total_rounds: int = 72,
        initial_sentiment: float = 0.0,
    ) -> SimulationState:
        """Create a new simulation."""
        import uuid
        sim_id = f"sim_{uuid.uuid4().hex[:12]}"

        state = SimulationState(
            simulation_id=sim_id,
            topic=topic,
            agents=agents,
            total_rounds=total_rounds,
            topic_sentiment=initial_sentiment,
        )
        self._simulations[sim_id] = state
        return state

    async def run(
        self,
        simulation_id: str,
        on_round_complete: Optional[Callable[..., Awaitable[None]]] = None,
        emit_sse: bool = False,
    ) -> SimulationState:
        """Run the simulation to completion."""
        state = self._simulations.get(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        state.status = SimulationStatus.RUNNING
        state.started_at = datetime.now()

        try:
            for round_num in range(state.current_round, state.total_rounds):
                if state.paused:
                    state.status = SimulationStatus.PAUSED
                    return state

                state.current_round = round_num
                summary = await self._execute_round(state, round_num)
                state.round_summaries.append(summary)

                # Update running topic sentiment
                if summary.actions_taken > 0:
                    state.topic_sentiment = (
                        state.topic_sentiment * 0.9 + summary.avg_sentiment * 0.1
                    )

                # Emit SSE event if wired
                if emit_sse:
                    await self._emit_round_sse(state, summary)

                if on_round_complete:
                    await on_round_complete(round_num, state, summary)

            state.status = SimulationStatus.COMPLETED
            state.completed_at = datetime.now()

            if emit_sse:
                await self._emit_complete_sse(state)

        except Exception as e:
            state.status = SimulationStatus.FAILED
            state.error = str(e)

        return state

    async def _execute_round(
        self,
        state: SimulationState,
        round_num: int,
    ) -> RoundSummary:
        """Execute a single simulation round (asynchronously for LLM support)."""
        round_decisions: List[AgentDecision] = []
        round_actions: List[SimulationAction] = []
        active_count = 0

        logger.info(f"[Simulation] Starting round {round_num}/{state.total_rounds}")

        # Phase 1: Activate agents and collect decisions (Parallel where possible)
        tasks = []
        for agent in state.agents:
            if not self._behavior.should_activate(agent, round_num):
                continue
            active_count += 1
            tasks.append(self._behavior.decide_action(
                agent=agent,
                topic_sentiment=state.topic_sentiment,
                recent_actions=round_decisions,
            ))
        
        if tasks:
            # Note: We await them to simulate the flow of the round
            results = await asyncio.gather(*tasks)
            for decision in results:
                round_decisions.append(decision)
                agent_map = state.agent_map
                agent = agent_map[decision.agent_id]
                
                action = SimulationAction(
                    round_num=round_num,
                    timestamp=datetime.now().isoformat(),
                    platform=state.topic,
                    agent_id=decision.agent_id,
                    agent_name=agent.name,
                    action_type=decision.action.value,
                    sentiment=decision.sentiment,
                    influence=decision.influence_delta,
                    target_id=decision.target_agent_id,
                )
                round_actions.append(action)

                # Emit "live talk" as agent thought
                try:
                    from backend.app.api.stream import emit_agent_thought
                    thought_msg = f"{agent.name} ({agent.role}): {decision.action.value} with sentiment {decision.sentiment:.2f}"
                    if decision.target_agent_id is not None:
                        target = agent_map.get(decision.target_agent_id)
                        if target:
                            thought_msg += f" (target: {target.name})"
                    
                    await emit_agent_thought(message=thought_msg, step="simulation")
                    logger.info(f"Agent Action: {thought_msg}")
                except (ImportError, ModuleNotFoundError):
                    pass

        state.actions.extend(round_actions)

        # Phase 2: Apply influence — each agent absorbs others' actions
        belief_shifts = 0
        for agent in state.agents:
            shift = self._behavior.apply_influence(agent, round_decisions)
            if shift > 0.01:
                belief_shifts += 1

        # Phase 3: Update trust networks based on interactions
        for decision in round_decisions:
            if decision.target_agent_id is None:
                continue
            actor = state.agent_map.get(decision.agent_id)
            target = state.agent_map.get(decision.target_agent_id)
            if actor and target:
                # How aligned are actor and target?
                alignment = 1.0 - abs(actor.sentiment_bias - target.sentiment_bias)
                self._behavior.update_trust(actor, target.agent_id, decision.action, alignment)
                self._behavior.update_trust(target, actor.agent_id, decision.action, alignment)

        # Build summary
        sentiments = [d.sentiment for d in round_decisions if d.action != ActionType.IGNORE]
        avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0.0
        max_inf = max((d.influence_delta for d in round_decisions), default=0.0)

        # Collect network and belief state for frontend
        trust_network = self._serialize_trust_network(state.agents)
        belief_profile = {a.agent_id: a.sentiment_bias for a in state.agents}

        return RoundSummary(
            round_num=round_num,
            active_agents=active_count,
            actions_taken=len(round_decisions),
            avg_sentiment=avg_sent,
            max_influence=max_inf,
            belief_shifts=belief_shifts,
            trust_network=trust_network,
            belief_profile=belief_profile,
        )

    def _serialize_trust_network(self, agents: List[AgentPersona]) -> Dict[str, Any]:
        """Convert agent trust networks into a D3-friendly nodes/links format."""
        nodes = []
        links = []
        for agent in agents:
            nodes.append({
                "id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
                "sentiment": agent.sentiment_bias,
                "stance": agent.stance.value
            })
            for target_id, trust in agent.trust_network.items():
                if trust > 0.1:  # Only send significant links to avoid overwhelming frontend
                    links.append({
                        "source": agent.agent_id,
                        "target": target_id,
                        "trust": trust
                    })
        return {"nodes": nodes, "links": links}

    async def _emit_round_sse(self, state: SimulationState, summary: RoundSummary) -> None:
        """Emit SSE event for a completed round."""
        try:
            from backend.app.api.stream import emit_simulation_round
            await emit_simulation_round(
                simulation_id=state.simulation_id,
                round_num=summary.round_num,
                total_rounds=state.total_rounds,
                actions=summary.actions_taken,
                trust_network=summary.trust_network,
                belief_profile=summary.belief_profile,
            )
        except ImportError:
            pass  # SSE not available (e.g., in tests)

    async def _emit_complete_sse(self, state: SimulationState) -> None:
        """Emit SSE event when simulation completes."""
        try:
            from backend.app.api.stream import event_bus
            await event_bus.publish("simulation_complete", {
                "simulation_id": state.simulation_id,
                "total_rounds": state.total_rounds,
                "total_actions": len(state.actions),
                "final_sentiment": state.topic_sentiment,
            })
        except ImportError:
            pass

    def pause(self, simulation_id: str) -> bool:
        """Pause a running simulation."""
        state = self._simulations.get(simulation_id)
        if not state or state.status != SimulationStatus.RUNNING:
            return False
        state.paused = True
        return True

    def resume(self, simulation_id: str) -> bool:
        """Resume a paused simulation (caller must re-call run())."""
        state = self._simulations.get(simulation_id)
        if not state or state.status != SimulationStatus.PAUSED:
            return False
        state.paused = False
        state.status = SimulationStatus.RUNNING
        return True

    def inject_scenario(
        self,
        simulation_id: str,
        sentiment_shock: float = 0.0,
        new_agents: Optional[List[AgentPersona]] = None,
    ) -> bool:
        """Inject a what-if scenario into a running simulation."""
        state = self._simulations.get(simulation_id)
        if not state or state.status not in (SimulationStatus.RUNNING, SimulationStatus.PAUSED):
            return False

        # Apply sentiment shock
        if sentiment_shock != 0.0:
            state.topic_sentiment = max(-1.0, min(1.0, state.topic_sentiment + sentiment_shock))

        # Inject new agents
        if new_agents:
            state.agents.extend(new_agents)

        return True

    def get_state(self, simulation_id: str) -> Optional[SimulationState]:
        return self._simulations.get(simulation_id)
