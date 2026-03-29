"""
Security layer for SelfMirror IDE.
Command allowlist, API key auth, and input sanitization.
"""

import os
import re
import shlex
from typing import Optional, List, Dict, Callable
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


# --- Command Validation Logic ---

def validate_python_m(args: List[str]) -> bool:
    """Only allow specific python modules via -m flag."""
    if len(args) < 3:
        return False
    if args[1] != "-m":
        return False
    module = args[2]
    allowed_modules = ["pytest", "json.tool", "venv", "pip"]
    # We allow 'pip' only for 'pip list' or 'pip show'
    if module == "pip":
        return len(args) >= 4 and args[3] in ["list", "show"]
    return module in allowed_modules

def validate_npm(args: List[str]) -> bool:
    """Only allow npm test, lint, build."""
    if len(args) < 2:
        return False
    subcommand = args[1]
    if subcommand == "run":
        return len(args) >= 3 and args[2] in ["test", "lint", "build"]
    return subcommand in ["test", "test:unit", "test:e2e"]

def validate_npx(args: List[str]) -> bool:
    """Only allow safe npx subcommands."""
    if len(args) < 2:
        return False
    subcommand = args[1]
    allowed_npx = ["tsc", "vitest", "ruff", "mypy"]
    return subcommand in allowed_npx

def validate_uv(args: List[str]) -> bool:
    """Only allow uv run python -m pytest or uv run ruff."""
    if len(args) < 2:
        return False
    if args[1] == "run":
        # Recursively validate the command after 'uv run'
        return validate_command_tokens(args[2:])
    return False

def validate_git(args: List[str]) -> bool:
    """Only allow safe, read-only git subcommands."""
    if len(args) < 2:
        return False
    subcommand = args[1]
    allowed_subcommands = ["status", "diff", "log", "show", "branch", "rev-parse"]
    return subcommand in allowed_subcommands

# Map base commands to validation functions (or None for always allowed)
ALLOWED_COMMANDS: Dict[str, Optional[Callable[[List[str]], bool]]] = {
    "pytest": None,
    "python": validate_python_m,
    "python3": validate_python_m,
    "uv": validate_uv,
    "npm": validate_npm,
    "npx": validate_npx,
    "ruff": None,
    "mypy": None,
    "git": validate_git,
    "ls": None,
    "cat": None,
    "head": None,
    "tail": None,
    "wc": None,
    "find": None,
    "grep": None,
    "echo": None,
    "pwd": None,
    "which": None,
    "env": None,
}

# Patterns that are ALWAYS blocked, even if base command is allowed.
BLOCKED_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\brm\s+-r\b",
    r"\brm\s+/",
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+checkout\s+\.",
    r"\bgit\s+clean\b",
    r"\bgit\s+config\b",
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
    # Sensitive file access
    r"\.env",
    r"\.git/",
    r"config/secrets",
]

def validate_command_tokens(tokens: List[str]) -> bool:
    """Internal helper to validate tokenized command."""
    if not tokens:
        return False
    
    base_cmd = tokens[0]
    if base_cmd not in ALLOWED_COMMANDS:
        return False
    
    validator = ALLOWED_COMMANDS[base_cmd]
    if validator:
        return validator(tokens)
    
    return True

def validate_command(command: str) -> dict:
    """
    Check if a command is safe to execute using tokenization.
    """
    cmd_stripped = command.strip()
    if not cmd_stripped:
        return {"allowed": False, "reason": "Empty command."}

    # 1. Check blocked patterns (regex)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            return {"allowed": False, "reason": f"Blocked pattern: {pattern}"}

    # 2. Tokenize and validate base command + arguments
    try:
        tokens = shlex.split(cmd_stripped)
    except ValueError as e:
        return {"allowed": False, "reason": f"Shell parsing error: {str(e)}"}

    if validate_command_tokens(tokens):
        return {"allowed": True}

    return {
        "allowed": False,
        "reason": f"Command or arguments not in allowlist: '{cmd_stripped.split()[0]}'"
    }
