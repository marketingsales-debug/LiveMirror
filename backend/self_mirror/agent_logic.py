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
        Execute a development goal autonomously.
        
        Returns a stream of thoughts (for SSE).
        """
        await _emit_thought(f"New goal received: {goal}", step="received")
        
        # 1. Gather context
        content = ""
        for f in context_files:
            await _emit_thought(f"Reading file for context: {f}", step="context")
            content += f"\nFILE: {f}\n{self.files.read_file(f)}\n"
        
        # 2. System Prompting
        # ... (keep existing prompt code) ...

        await _emit_thought("Analyzing requirements and planning code changes...", step="thinking")
        response = await self.llm.chat(messages)
        await _emit_thought(response, step="thought")

        # 4. Parse and Execute
        if "WRITE_FILE" in response:
            await _emit_action("WRITE_FILE", {"details": "Applying suggested file change..."})
            # Logic for actual write would go here...

        return [response]
