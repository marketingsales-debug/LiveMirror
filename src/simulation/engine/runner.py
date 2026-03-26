"""
Simulation Runner — executes forward simulations with calibrated agents.
Owner: Claude

Based on MiroFish's OASIS simulation runner, enhanced with:
- Real-time calibration against live data
- Agent belief evolution
- Prediction validation hooks
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

from ...shared.types import AgentPersona, Prediction


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
    action_type: str  # CREATE_POST, COMMENT, LIKE, RETWEET, etc.
    content: str = ""
    target_id: Optional[int] = None  # post or agent being responded to
    engagement: Dict[str, int] = field(default_factory=dict)


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
    predictions: List[Prediction] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


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

    def __init__(self):
        self._simulations: Dict[str, SimulationState] = {}

    def create_simulation(
        self,
        topic: str,
        agents: List[AgentPersona],
        total_rounds: int = 72,
    ) -> SimulationState:
        """Create a new simulation."""
        import uuid
        sim_id = f"sim_{uuid.uuid4().hex[:12]}"

        state = SimulationState(
            simulation_id=sim_id,
            topic=topic,
            agents=agents,
            total_rounds=total_rounds,
        )
        self._simulations[sim_id] = state
        return state

    async def run(
        self,
        simulation_id: str,
        on_round_complete: Optional[Callable] = None,
    ) -> SimulationState:
        """Run the simulation to completion."""
        state = self._simulations.get(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        state.status = SimulationStatus.RUNNING
        state.started_at = datetime.now()

        try:
            for round_num in range(state.current_round, state.total_rounds):
                state.current_round = round_num
                # TODO: implement actual simulation round logic
                # - activate agents based on time config
                # - agents decide actions
                # - execute actions
                # - update trust/belief networks
                # - log actions

                if on_round_complete:
                    on_round_complete(round_num, state)

            state.status = SimulationStatus.COMPLETED
            state.completed_at = datetime.now()

        except Exception as e:
            state.status = SimulationStatus.FAILED
            state.error = str(e)

        return state

    def inject_scenario(
        self,
        simulation_id: str,
        scenario: str,
    ) -> bool:
        """Inject a what-if scenario into a running simulation."""
        state = self._simulations.get(simulation_id)
        if not state or state.status != SimulationStatus.RUNNING:
            return False
        # TODO: implement scenario injection
        return True

    def get_state(self, simulation_id: str) -> Optional[SimulationState]:
        return self._simulations.get(simulation_id)
