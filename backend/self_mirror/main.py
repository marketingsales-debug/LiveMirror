"""
SelfMirror API — Finalized v2.0 Interface.
Wires the frontend to the LangGraph Research Board and Secret Manager.
"""

import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, conint, conlist, constr
from typing import List

from .security import require_auth
from .agent_logic import AgentLoop

router = APIRouter()

# Resolve PROJECT_ROOT relative to this file's directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

MAX_GOAL_LENGTH = 500
MAX_CONTEXT_FILES = 50
MAX_CONTEXT_PATH_LENGTH = 200
MAX_COMMAND_LENGTH = 2048
MAX_SECRET_NAME_LENGTH = 128
MAX_SECRET_VALUE_LENGTH = 4096
SECRET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
EXEC_BLOCKED_PATTERN = re.compile(r"\$\(|`")


def _ensure_no_null(value: str, label: str) -> None:
    if "\x00" in value:
        raise HTTPException(status_code=422, detail=f"Invalid {label}.")


def _validate_context_files(context_files: List[str]) -> None:
    for path in context_files:
        _ensure_no_null(path, "context file path")
        path_obj = Path(path)
        if path_obj.is_absolute() or ".." in path_obj.parts:
            raise HTTPException(status_code=422, detail="Invalid context file path.")


def _validate_goal(goal: str) -> None:
    _ensure_no_null(goal, "goal")


def _validate_exec_command(command: str) -> None:
    _ensure_no_null(command, "command")
    if EXEC_BLOCKED_PATTERN.search(command):
        raise HTTPException(status_code=422, detail="Command contains forbidden shell substitution.")


def _validate_secret_value(value: str) -> None:
    _ensure_no_null(value, "secret value")

class GoalRequest(BaseModel):
    goal: constr(strip_whitespace=True, min_length=1, max_length=MAX_GOAL_LENGTH)
    context_files: conlist(
        constr(strip_whitespace=True, min_length=1, max_length=MAX_CONTEXT_PATH_LENGTH),
        max_length=MAX_CONTEXT_FILES,
    ) = Field(default_factory=list)
    max_iterations: conint(ge=1, le=50) = 10


class GoalResponse(BaseModel):
    thoughts: List[str]
    status: str

class SecretRequest(BaseModel):
    name: constr(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_SECRET_NAME_LENGTH,
        pattern=SECRET_NAME_PATTERN.pattern,
    )
    value: constr(strip_whitespace=True, min_length=1, max_length=MAX_SECRET_VALUE_LENGTH)


class ExecRequest(BaseModel):
    command: constr(strip_whitespace=True, min_length=1, max_length=MAX_COMMAND_LENGTH)


@router.post("/goal", response_model=GoalResponse)
async def start_goal(request: GoalRequest, _auth: str = Depends(require_auth)):
    """Start the LangGraph Research Board for a goal (auth required)."""
    try:
        _validate_goal(request.goal)
        _validate_context_files(request.context_files)
        loop = AgentLoop(PROJECT_ROOT)
        thoughts = await loop.run_goal(
            request.goal,
            request.context_files,
            max_iterations=request.max_iterations,
        )
        return GoalResponse(thoughts=thoughts, status="completed")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Agent Board failed.")


@router.get("/files")
async def list_workspace_files(_auth: str = Depends(require_auth)):
    """Returns all files the agent can see (auth required)."""
    try:
        loop = AgentLoop(PROJECT_ROOT)
        return {"files": loop.files.list_files()}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list files.")


@router.post("/exec")
async def run_command(request: ExecRequest, _auth: str = Depends(require_auth)):
    """Execute a command inside the SelfMirror workspace (auth required)."""
    try:
        _validate_exec_command(request.command)
        loop = AgentLoop(PROJECT_ROOT)
        return loop.exec.run_command(request.command)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Command execution failed.")


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
    _validate_secret_value(request.value)
    db = LessonLearntStore()
    db.set_secret(request.name, request.value)
    return {"status": "updated", "key": request.name.upper()}

@router.delete("/secrets/{key_name}")
async def delete_secret(key_name: str, _auth: str = Depends(require_auth)):
    """Delete a managed secret (auth required)."""
    if len(key_name) > MAX_SECRET_NAME_LENGTH or "\x00" in key_name:
        raise HTTPException(status_code=422, detail="Invalid secret name.")
    if not SECRET_NAME_PATTERN.fullmatch(key_name):
        raise HTTPException(status_code=422, detail="Invalid secret name.")
    from src.memory.lesson_learnt import LessonLearntStore
    db = LessonLearntStore()
    db.delete_secret(key_name)
    return {"status": "deleted", "key": key_name.upper()}
