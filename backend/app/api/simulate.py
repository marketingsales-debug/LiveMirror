"""Simulation API endpoints — manage simulations and scenarios."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter()


class SimulateRequest(BaseModel):
    """Request to run a simulation."""
    topic: str
    scenario: Optional[str] = None  # "what-if" injection
    agent_count: int = 50
    simulation_hours: int = 72
    platforms: List[str] = ["twitter", "reddit"]


class ScenarioRequest(BaseModel):
    """Inject a what-if scenario into a running simulation."""
    simulation_id: str
    scenario: str  # e.g., "Company X announces layoffs"
    inject_at_round: Optional[int] = None  # None = next round


@router.post("/start")
async def start_simulation(request: SimulateRequest):
    """Start a new simulation."""
    return {"simulation_id": "sim_placeholder", "status": "queued"}


@router.post("/scenario")
async def inject_scenario(request: ScenarioRequest):
    """Inject a what-if scenario into a running simulation."""
    return {"simulation_id": request.simulation_id, "scenario_injected": True}


@router.get("/status/{simulation_id}")
async def simulation_status(simulation_id: str):
    """Get simulation status."""
    return {"simulation_id": simulation_id, "status": "not_implemented"}


@router.get("/agents/{simulation_id}")
async def list_agents(simulation_id: str):
    """List all agents in a simulation."""
    return {"simulation_id": simulation_id, "agents": []}


@router.get("/agents/{simulation_id}/{agent_id}/chat")
async def chat_with_agent(simulation_id: str, agent_id: int, message: str = ""):
    """Chat with a specific agent in the simulation."""
    return {"agent_id": agent_id, "response": "not_implemented"}
