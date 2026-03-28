"""
SelfMirror API — the interface for the autonomous agent.
FastAPI router for coordinating agent goals and the self-evolution loop.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from .agent_logic import AgentLoop
from .services import FileService, ExecutionService

router = APIRouter()

# Share one loop instance for now (relative to project root)
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
_loop: Optional[AgentLoop] = None

def get_loop() -> AgentLoop:
    """Get the shared agent loop instance."""
    global _loop
    if _loop is None:
        _loop = AgentLoop(workspace_root=PROJECT_ROOT)
    return _loop

class GoalRequest(BaseModel):
    """Initial request to give the agent a development goal."""
    goal: str
    context_files: List[str] = []

class GoalResponse(BaseModel):
    """Response from the agent's first thought process."""
    thoughts: List[str]
    status: str

@router.post("/goal", response_model=GoalResponse)
async def start_goal(request: GoalRequest):
    """Start the 'Think-Apply-Verify' cycle for a goal."""
    loop = get_loop()
    try:
        thoughts = await loop.run_goal(request.goal, request.context_files)
        return GoalResponse(thoughts=thoughts, status="thinking")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed to think: {e}")

@router.get("/files")
async def list_workspace_files():
    """Returns all files the agent can see."""
    loop = get_loop()
    try:
        files = loop.files.list_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exec")
async def run_command(command: str):
    """Manually run a terminal command on behalf of the agent."""
    loop = get_loop()
    try:
        result = loop.exec.run_command(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
