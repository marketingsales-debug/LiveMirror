"""
Agent Logic — the 'Brain' of the SelfMirror IDE.
Implements the autonomous loop: Understand -> Plan -> Execute -> Verify.
"""

import os
import json
import httpx
from typing import List, Dict, Any, Optional
from .services import FileService, ExecutionService

# SSE Emitters (lazy import to avoid circular deps)
async def _emit_thought(message: str, step: str = "thinking"):
    try:
        from backend.app.api.stream import emit_agent_thought
        await emit_agent_thought(message, step)
    except ImportError:
        pass

async def _emit_action(action_type: str, details: Dict[str, Any]):
    try:
        from backend.app.api.stream import emit_agent_action
        await emit_agent_action(action_type, details)
    except ImportError:
        pass

class LLMClient:
    """Interact with the configured OpenAI-compatible LLM."""
    
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "missing")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL_NAME", "gpt-4o")

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send a chat completion request."""
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
                    timeout=30
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"Error: LLM call failed: {str(e)}"

class AgentLoop:
    """The autonomous reasoning loop for SelfMirror."""
    
    def __init__(self, workspace_root: str):
        self.files = FileService(workspace_root)
        self.exec = ExecutionService(workspace_root)
        self.llm = LLMClient()
        self.history: List[Dict[str, Any]] = []

    async def run_goal(self, goal: str, context_files: List[str] = []) -> List[str]:
        """
        Execute a development goal autonomously with automated verification and rollbacks.
        """
        await _emit_thought(f"Initiating goal: {goal}", step="received")
        
        # 1. Gather initial context
        system_prompt = """
You are the SelfMirror Autonomous IDE Agent. Your goal is to help the user develop and maintain this repository.
You operate in a loop: THOUGHT -> ACTION -> VERIFICATION.

For every step, you MUST respond in the following format:
THOUGHT: <your reasoning about the current state and next steps>
ACTION: { "type": "WRITE_FILE|READ_FILE|RUN_COMMAND", "path": "file_path", "content": "file_content", "command": "shell_command" }
VERIFY: <the shell command to run to verify the success of your action, e.g. 'pytest' or 'npm run lint'>

If you have completed the goal, respond with:
THOUGHT: Goal achieved.
ACTION: { "type": "COMPLETE" }

Safety Rules:
- Never delete core project files.
- Always use the VERIFY step to ensure no regressions.
- If a verification fails, the system will automatically roll back your change.
"""
        
        context_content = ""
        for f in context_files:
            await _emit_thought(f"Reading {f} for context...", step="context")
            content = self.files.read_file(f)
            context_content += f"\nFILE: {f}\n{content}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context files:\n{context_content}\n\nGoal: {goal}"}
        ]

        # 2. Reasoning Loop
        max_iterations = 5
        for i in range(max_iterations):
            await _emit_thought(f"Reasoning loop iteration {i+1}/{max_iterations}...", step="thinking")
            response = await self.llm.chat(messages)
            await _emit_thought(response, step="thought")
            messages.append({"role": "assistant", "content": response})

            # Parse Action
            try:
                action_line = [l for l in response.split('\n') if l.startswith('ACTION:')][0]
                action_data = json.loads(action_line.replace('ACTION:', '').strip())
                action_type = action_data.get("type")
            except Exception as e:
                await _emit_thought(f"Failed to parse action: {str(e)}", step="error")
                break

            if action_type == "COMPLETE":
                await _emit_thought("Goal completed successfully.", step="done")
                break

            # Execute Action
            if action_type == "READ_FILE":
                path = action_data.get("path")
                await _emit_action("READ_FILE", {"path": path})
                result = self.files.read_file(path)
                messages.append({"role": "user", "content": f"READ_FILE Result:\n{result}"})

            elif action_type == "WRITE_FILE":
                path = action_data.get("path")
                content = action_data.get("content")
                verify_cmd = [l for l in response.split('\n') if l.startswith('VERIFY:')][0].replace('VERIFY:', '').strip()
                
                await _emit_action("WRITE_FILE", {"path": path, "verify": verify_cmd})
                
                # Backup -> Write -> Verify
                self.files.backup_file(path)
                self.files.write_file(path, content)
                
                await _emit_thought(f"Verifying change with: {verify_cmd}", step="verifying")
                check = self.exec.run_command(verify_cmd)
                
                if check["success"]:
                    await _emit_thought("Verification PASSED.", step="success")
                    self.files.delete_backup(path)
                    messages.append({"role": "user", "content": f"SUCCESS: {verify_cmd} passed."})
                else:
                    await _emit_thought(f"Verification FAILED: {check['stderr']}. Rolling back...", step="rollback")
                    self.files.restore_file(path)
                    messages.append({"role": "user", "content": f"FAILURE: {verify_cmd} failed. File rolled back. Error: {check['stderr']}"})

            elif action_type == "RUN_COMMAND":
                cmd = action_data.get("command")
                await _emit_action("RUN_COMMAND", {"command": cmd})
                res = self.exec.run_command(cmd)
                messages.append({"role": "user", "content": f"RUN_COMMAND Result (success={res['success']}):\n{res['stdout']}\n{res['stderr']}"})

        return [m["content"] for m in messages if m["role"] == "assistant"]

