"""
Security layer for SelfMirror IDE.
Command allowlist, API key auth, and input sanitization.
"""

import os
import re
import shlex
from typing import Optional
from fastapi import HTTPException, Header


# --- API Key Authentication ---

SELFMIRROR_API_KEY = os.getenv("SELFMIRROR_API_KEY", "")


async def require_auth(x_api_key: Optional[str] = Header(None)) -> str:
    """FastAPI dependency — rejects requests without valid API key."""
    if not SELFMIRROR_API_KEY:
        # No key configured = dev mode, allow all
        return "dev-mode"
    if x_api_key != SELFMIRROR_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")
    return x_api_key


# --- Command Allowlist ---

# Prefix patterns that the agent is allowed to run.
# Anything not matching is blocked before reaching subprocess.
ALLOWED_COMMAND_PREFIXES = [
    # Testing
    "pytest",
    "python -m pytest",
    "uv run python -m pytest",
    "npm test",
    "npm run test",
    "npx vitest",
    # Linting / type checking
    "npm run lint",
    "npm run build",
    "npx tsc",
    "ruff check",
    "ruff format",
    "mypy",
    # Git read-only
    "git status",
    "git diff",
    "git log",
    "git show",
    "git branch",
    # Python
    "python -m",
    "uv run",
    # Info commands
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "find",
    "grep",
    "echo",
    "pwd",
    "which",
    "env",
]

# Patterns that are ALWAYS blocked, even if prefix matches.
BLOCKED_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\brm\s+-r\b",
    r"\brm\s+/",
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+checkout\s+\.",
    r"\bgit\s+clean\b",
    r"\bcurl\b.*\|\s*(?:bash|sh|zsh)",
    r"\bwget\b.*\|\s*(?:bash|sh|zsh)",
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\bsudo\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/",
    r"\bkill\b",
    r"\bkillall\b",
    r"\bshutdown\b",
    r"\breboot\b",
]


def validate_command(command: str) -> dict:
    """
    Check if a command is safe to execute.

    Returns:
        {"allowed": True} or {"allowed": False, "reason": "..."}
    """
    cmd_stripped = command.strip()

    if not cmd_stripped:
        return {"allowed": False, "reason": "Empty command."}

    # 1. Check blocked patterns first (highest priority)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            return {"allowed": False, "reason": f"Blocked pattern: {pattern}"}

    # 2. Check if command starts with an allowed prefix
    for prefix in ALLOWED_COMMAND_PREFIXES:
        if cmd_stripped.startswith(prefix):
            return {"allowed": True}

    return {
        "allowed": False,
        "reason": f"Command not in allowlist. Starts with: '{cmd_stripped.split()[0]}'"
    }
