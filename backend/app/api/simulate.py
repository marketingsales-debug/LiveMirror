"""
Simulation API endpoints — manage simulations and scenarios.
Owner: Claude

Wires the Vue dashboard's "Run Simulation" button to the real
SimulationRunner + AgentFactory + KnowledgeGraph pipeline.
"""

import sys
import os
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, conint, constr
from typing import List, Optional

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.simulation.engine.runner import SimulationRunner
from src.simulation.agents.factory import AgentFactory
from src.graph.knowledge.graph import KnowledgeGraph
from src.shared.types import Platform

router = APIRouter()
logger = logging.getLogger(__name__)

# Shared instances (in-memory for v1 — will move to DI container later)
_runner = SimulationRunner()
_factory = AgentFactory()
_graph = KnowledgeGraph()


def set_graph(graph: KnowledgeGraph) -> None:
    """Allow the pipeline to share its graph instance."""
    global _graph
    _graph = graph


class SimulateRequest(BaseModel):
    """Request to run a simulation."""
    topic: constr(strip_whitespace=True, min_length=1, max_length=200)
    scenario: Optional[constr(strip_whitespace=True, min_length=1, max_length=500)] = None
    agent_count: conint(ge=1, le=200) = 50
    total_rounds: conint(ge=1, le=500) = 72
    platforms: List[Platform] = Field(default_factory=lambda: [Platform.TWITTER, Platform.REDDIT], min_items=1)


class ScenarioRequest(BaseModel):
    """Inject a what-if scenario into a running simulation."""
    simulation_id: str
    scenario: str
    sentiment_shock: float = 0.0
    inject_at_round: Optional[int] = None


class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    topic: str
    agent_count: int
    total_rounds: int


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(request: SimulateRequest, background_tasks: BackgroundTasks):
    """
    Start a new simulation.

    Creates agents from the knowledge graph (or synthetic if graph is empty),
    then runs the simulation in the background with SSE events emitted each round.
    """
    # Create agents from graph or synthetic fallback
    if _graph.entity_count > 0:
        agents = _factory.from_graph(
            _graph,
            query=request.topic,
            max_agents=request.agent_count,
        )
    else:
        # No graph data yet — create synthetic agents
        agents = [
            _factory.create_synthetic(name=f"Agent_{i}")
            for i in range(request.agent_count)
        ]

    # Create simulation
    state = _runner.create_simulation(
        topic=request.topic,
        agents=agents,
        total_rounds=request.total_rounds,
    )

    # Run in background so the API returns immediately
    background_tasks.add_task(_run_simulation_bg, state.simulation_id)

    return SimulationResponse(
        simulation_id=state.simulation_id,
        status="running",
        topic=request.topic,
        agent_count=len(agents),
        total_rounds=request.total_rounds,
    )


async def _run_simulation_bg(simulation_id: str) -> None:
    """Background task that runs the simulation with SSE emission."""
    try:
        await _runner.run(simulation_id, emit_sse=True)
    except Exception:
        logger.exception("[SimulationAPI] Simulation %s failed", simulation_id)


@router.post("/scenario")
async def inject_scenario(request: ScenarioRequest):
    """Inject a what-if scenario into a running simulation."""
    state = _runner.get_state(request.simulation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    success = _runner.inject_scenario(
        simulation_id=request.simulation_id,
        sentiment_shock=request.sentiment_shock,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Simulation is not running or paused")

    return {"simulation_id": request.simulation_id, "scenario_injected": True}


@router.get("/status/{simulation_id}")
async def simulation_status(simulation_id: str):
    """Get simulation status and summary stats."""
    state = _runner.get_state(simulation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {
        "simulation_id": simulation_id,
        "status": state.status.value,
        "current_round": state.current_round,
        "total_rounds": state.total_rounds,
        "agent_count": len(state.agents),
        "total_actions": len(state.actions),
        "topic_sentiment": state.topic_sentiment,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        "error": state.error,
    }


@router.post("/pause/{simulation_id}")
async def pause_simulation(simulation_id: str):
    """Pause a running simulation."""
    if not _runner.pause(simulation_id):
        raise HTTPException(status_code=400, detail="Cannot pause — not running")
    return {"simulation_id": simulation_id, "status": "paused"}


@router.post("/resume/{simulation_id}")
async def resume_simulation(simulation_id: str, background_tasks: BackgroundTasks):
    """Resume a paused simulation."""
    if not _runner.resume(simulation_id):
        raise HTTPException(status_code=400, detail="Cannot resume — not paused")
    background_tasks.add_task(_run_simulation_bg, simulation_id)
    return {"simulation_id": simulation_id, "status": "running"}


@router.get("/agents/{simulation_id}")
async def list_agents(simulation_id: str):
    """List all agents in a simulation with current state."""
    state = _runner.get_state(simulation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agents = [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "role": a.role.value,
            "stance": a.stance.value,
            "sentiment_bias": round(a.sentiment_bias, 3),
            "influence_weight": round(a.influence_weight, 2),
            "activity_level": round(a.activity_level, 2),
            "belief_shifts": len(a.belief_history),
        }
        for a in state.agents
    ]
    return {"simulation_id": simulation_id, "agents": agents}
