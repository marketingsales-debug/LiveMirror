"""
SelfMirror API — the interface for the autonomous agent.
FastAPI router with API key auth and sandboxed execution.
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from .agent_logic import AgentLoop
from .security import require_auth

router = APIRouter()

# Resolve PROJECT_ROOT relative to this file's directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class GoalRequest(BaseModel):
    goal: str
    context_files: List[str] = []
    max_iterations: int = 10


class GoalResponse(BaseModel):
    thoughts: List[str]
    status: str


@router.post("/goal", response_model=GoalResponse)
async def start_goal(request: GoalRequest, _auth: str = Depends(require_auth)):
    """Start the Think-Apply-Verify cycle for a goal (auth required)."""
    # Instantiate a fresh loop per request for concurrency safety
    loop = AgentLoop(workspace_root=PROJECT_ROOT)
    try:
        thoughts = await loop.run_goal(
            request.goal,
            request.context_files,
            max_iterations=request.max_iterations,
        )
        return GoalResponse(thoughts=thoughts, status="completed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")


@router.get("/files")
async def list_workspace_files(_auth: str = Depends(require_auth)):
    """Returns all files the agent can see (auth required)."""
    loop = AgentLoop(workspace_root=PROJECT_ROOT)
    try:
        files = loop.files.list_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exec")
async def run_command(command: str, _auth: str = Depends(require_auth)):
    """Run a terminal command — validated against allowlist (auth required)."""
    loop = AgentLoop(workspace_root=PROJECT_ROOT)
    try:
        result = loop.exec.run_command(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
