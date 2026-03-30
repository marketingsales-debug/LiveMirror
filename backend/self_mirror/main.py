"""
SelfMirror API — Finalized v2.0 Interface.
Wires the frontend to the LangGraph Research Board and Secret Manager.
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

class SecretRequest(BaseModel):
    name: str
    value: str


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
    # Simple placeholder for file listing
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

@router.get("/secrets")
async def list_secrets(_auth: str = Depends(require_auth)):
    """List managed secret names (auth required)."""
    from src.memory.lesson_learnt import LessonLearntStore
    db = LessonLearntStore()
    return {"secrets": db.list_secrets()}

@router.post("/secrets")
async def update_secret(request: SecretRequest, _auth: str = Depends(require_auth)):
    """Update or create a secret key (auth required)."""
    from src.memory.lesson_learnt import LessonLearntStore
    db = LessonLearntStore()
    db.set_secret(request.name, request.value)
    return {"status": "updated", "key": request.name.upper()}

@router.delete("/secrets/{key_name}")
async def delete_secret(key_name: str, _auth: str = Depends(require_auth)):
    """Delete a managed secret (auth required)."""
    from src.memory.lesson_learnt import LessonLearntStore
    db = LessonLearntStore()
    db.delete_secret(key_name)
    return {"status": "deleted", "key": key_name.upper()}
