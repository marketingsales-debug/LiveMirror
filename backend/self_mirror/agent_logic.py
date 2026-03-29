"""
Agent Logic — the 'Brain' of the SelfMirror IDE.
Implements the autonomous loop: Think -> Act -> Verify with rollback.
"""

import os
import json
import re
import httpx
from typing import List, Dict, Any, Optional
from .services import FileService, get_execution_service


# SSE Emitters (lazy import to avoid circular deps)
async def _emit_thought(message: str, step: str = "thinking") -> None:
    try:
        from backend.app.api.stream import emit_agent_thought
        await emit_agent_thought(message, step)
    except ImportError:
        pass


async def _emit_action(action_type: str, details: Dict[str, Any]) -> None:
    try:
        from backend.app.api.stream import emit_agent_action
        await emit_agent_action(action_type, details)
    except ImportError:
        pass


# --- LiveMirror-Aware System Prompt ---

SYSTEM_PROMPT = """You are the SelfMirror Autonomous IDE Agent for the LiveMirror project.

## Project Context
LiveMirror is a real-time, self-calibrating prediction engine:
- Backend: Python 3.11 + FastAPI (backend/app/)
- Frontend: Vue 3 + Vite + TypeScript (frontend/)
- Fusion Engine: Multimodal analysis — text, audio, video, sentiment (src/fusion/)
- Simulation: 50+ synthetic agents, 72-round tournaments (src/simulation/)
- Orchestrator: Full pipeline — ingest → fuse → analyze → graph → simulate → debate → predict → learn (src/orchestrator/)
- Tests: pytest (tests/), 113+ passing

## File Ownership
- Claude owns: src/ingestion/, src/graph/, src/simulation/, src/fusion/, backend/, src/orchestrator/, src/prediction/, src/learning/
- Gemini owns: src/analysis/, frontend/
- Shared (lock required): src/shared/, src/api/
- NEVER modify files you don't own without reading .collab/RULES.md

## Response Format
For EVERY step, respond EXACTLY in this format:

THOUGHT: <your reasoning>
ACTION: {"type": "READ_FILE", "path": "relative/path"}
ACTION: {"type": "WRITE_FILE", "path": "relative/path", "content": "file content here"}
ACTION: {"type": "RUN_COMMAND", "command": "pytest tests/unit/fusion/ -v"}
VERIFY: <shell command to confirm success, e.g. 'pytest tests/' or 'npm run build'>

When done:
THOUGHT: Goal achieved.
ACTION: {"type": "COMPLETE"}

## Safety Rules
- NEVER delete core project files
- NEVER modify Gemini-owned files (frontend/, src/analysis/)
- ALWAYS verify with tests after writing
- The system auto-rolls back if VERIFY fails
- Commands are validated against an allowlist — only test/lint/git-read commands work
- Your environment may be a container; networking is DISABLED for security.

## Allowed Commands
pytest, python -m pytest, npm test, npm run lint, npm run build, npx tsc, npx vitest, ruff check, git status, git diff, git log, ls, cat, head, grep, find
"""


class LLMClient:
    """Interact with the configured OpenAI-compatible LLM."""

    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL_NAME", "gpt-4o")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "missing")

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.is_configured():
            return "Error: LLM_API_KEY not set. Set it in .env to enable the agent."

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.2,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"Error: LLM call failed: {str(e)}"


def _parse_action(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract ACTION JSON from LLM response. Handles common formatting issues:
    - ACTION: {...}
    - ACTION:{"type":...}
    - JSON embedded in markdown code blocks
    """
    # Try direct match first
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("ACTION:"):
            json_str = line[len("ACTION:"):].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # Try extracting JSON from code blocks
    json_match = re.search(r'ACTION:\s*```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding any JSON object after ACTION
    json_match = re.search(r'ACTION:\s*(\{[^}]+\})', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _parse_verify(response: str) -> Optional[str]:
    """Extract VERIFY command from LLM response."""
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("VERIFY:"):
            cmd = line[len("VERIFY:"):].strip()
            if cmd:
                return cmd
    return None


class AgentLoop:
    """The autonomous reasoning loop for SelfMirror."""

    def __init__(self, workspace_root: str):
        self.files = FileService(workspace_root)
        self.exec = get_execution_service(workspace_root)
        self.llm = LLMClient()

    async def run_goal(
        self,
        goal: str,
        context_files: Optional[List[str]] = None,
        max_iterations: int = 10,
    ) -> List[str]:
        """Execute a development goal with Think-Act-Verify loop."""
        context_files = context_files or []
        max_iterations = min(max_iterations, 20)  # hard cap

        await _emit_thought(f"Initiating goal: {goal}", step="received")

        if not self.llm.is_configured():
            await _emit_thought("LLM_API_KEY not configured. Cannot proceed.", step="error")
            return ["Error: LLM_API_KEY not set."]

        # 1. Gather context
        context_content = ""
        for f in context_files:
            await _emit_thought(f"Reading {f} for context...", step="context")
            content = self.files.read_file(f)
            context_content += f"\nFILE: {f}\n{content}\n"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context files:\n{context_content}\n\nGoal: {goal}"},
        ]

        # 2. Reasoning Loop
        parse_failures = 0
        for i in range(max_iterations):
            await _emit_thought(f"Iteration {i + 1}/{max_iterations}...", step="thinking")

            response = await self.llm.chat(messages)
            await _emit_thought(response, step="thought")
            messages.append({"role": "assistant", "content": response})

            # Check for LLM errors
            if response.startswith("Error:"):
                await _emit_thought(f"LLM error: {response}", step="error")
                break

            # Parse action
            action_data = _parse_action(response)
            if action_data is None:
                parse_failures += 1
                await _emit_thought(
                    f"Could not parse ACTION (attempt {parse_failures}/3). Re-prompting...",
                    step="error",
                )
                if parse_failures >= 3:
                    await _emit_thought("Too many parse failures. Stopping.", step="error")
                    break
                messages.append({
                    "role": "user",
                    "content": "I could not parse your ACTION. Please respond EXACTLY in the format: ACTION: {\"type\": \"...\", ...}",
                })
                continue

            parse_failures = 0  # reset on success
            action_type = action_data.get("type", "")

            # COMPLETE
            if action_type == "COMPLETE":
                await _emit_thought("Goal completed.", step="done")
                break

            # READ_FILE
            elif action_type == "READ_FILE":
                path = action_data.get("path", "")
                await _emit_action("READ_FILE", {"path": path})
                result = self.files.read_file(path)
                messages.append({"role": "user", "content": f"READ_FILE result:\n{result}"})

            # WRITE_FILE
            elif action_type == "WRITE_FILE":
                path = action_data.get("path", "")
                content = action_data.get("content", "")
                verify_cmd = _parse_verify(response) or "pytest tests/ -x -q"

                await _emit_action("WRITE_FILE", {"path": path, "verify": verify_cmd})

                self.files.backup_file(path)
                self.files.write_file(path, content)

                await _emit_thought(f"Verifying with: {verify_cmd}", step="verifying")
                check = self.exec.run_command(verify_cmd)

                if check["success"]:
                    await _emit_thought("Verification PASSED.", step="success")
                    self.files.delete_backup(path)
                    messages.append({"role": "user", "content": f"SUCCESS: {verify_cmd} passed."})
                else:
                    await _emit_thought(
                        f"Verification FAILED. Rolling back. Error: {check['stderr'][:500]}",
                        step="rollback",
                    )
                    self.files.restore_file(path)
                    messages.append({
                        "role": "user",
                        "content": f"FAILURE: {verify_cmd} failed. File rolled back.\nError: {check['stderr'][:500]}",
                    })

            # RUN_COMMAND
            elif action_type == "RUN_COMMAND":
                cmd = action_data.get("command", "")
                await _emit_action("RUN_COMMAND", {"command": cmd})
                res = self.exec.run_command(cmd)
                messages.append({
                    "role": "user",
                    "content": f"RUN_COMMAND (success={res['success']}):\n{res['stdout'][:3000]}\n{res['stderr'][:1000]}",
                })

            else:
                messages.append({
                    "role": "user",
                    "content": f"Unknown action type: '{action_type}'. Use READ_FILE, WRITE_FILE, RUN_COMMAND, or COMPLETE.",
                })

        return [m["content"] for m in messages if m["role"] == "assistant"]

