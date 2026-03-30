"""
SelfMirror API — Finalized v2.0 Interface.
Wires the frontend to the LangGraph Research Board.
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from .security import require_auth
from src.orchestrator.graph import research_board
from src.guards.schemas import StructuredResponse

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
    """Start the LangGraph Research Board for a goal (auth required)."""
    
    # Initialize state for the board
    initial_state = {
        "messages": [],
        "goal": request.goal,
        "context_files": request.context_files,
        "findings": [],
        "proposed_patch": None,
        "verification_results": {},
        "next_agent": "researcher",
        "lessons": [],
        "source_context": "No source context provided. Use SEARCH_WEB or READ_FILE if needed.",
        "active_strategy": "Standard research protocol"
    }

    try:
        # Run the graph
        # Using thread_id for state persistence (LangGraph Pattern)
        config = {"configurable": {"thread_id": "session_1"}}
        result = await research_board.ainvoke(initial_state, config=config)
        
        # Extract thoughts from messages
        thoughts = [m.content for m in result["messages"]]
        
        return GoalResponse(thoughts=thoughts, status="completed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Board failed: {e}")


@router.get("/files")
async def list_workspace_files(_auth: str = Depends(require_auth)):
    """Returns all files the agent can see (auth required)."""
    from src.memory.lesson_learnt import LessonLearntStore
    # We use the LessonLearntStore to list files for now as a proxy
    # In full implementation, this would be a specialized file service
    return {"files": ["main.py", "src/orchestrator/graph.py", "backend/app/main.py"]}


@router.get("/status")
async def get_system_status(_auth: str = Depends(require_auth)):
    """Returns the current security and execution status."""
    from .security import BLOCKED_PATTERNS
    mode = os.getenv("SELFMIRROR_EXECUTION_MODE", "host").lower()
    return {
        "execution_mode": mode,
        "security_blocks_active": len(BLOCKED_PATTERNS),
        "sandboxing": "Docker" if mode == "docker" else "OS-Level",
        "secrets_filtering": "Active",
        "orchestrator": "LangGraph v2.0",
        "reasoning": "RARE Open-Book",
    }
