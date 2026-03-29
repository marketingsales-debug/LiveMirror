"""
Generative Social Agents.
Implements personality, memory streams, and reflection.
Extracted from Stanford Generative Agents and SocioVerse patterns.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SocialAgent:
    """A generative agent that learns and reacts to social contagion."""
    id: str
    name: str
    personality: str           # "skeptic", "fomo_trader", "whale", "bot"
    susceptibility: float      # 0.0 (immune) to 1.0 (instant believer)
    memory: List[str] = field(default_factory=list)
    beliefs: str = "Standard market participant mindset."

    async def observe(self, signal_content: str, source: str, round_num: int):
        """Memory Stream: Accumulate observations."""
        self.memory.append(f"Round {round_num}: Saw '{signal_content}' from {source}")

    async def react(self, signal_content: str, llm_fn: Callable) -> Dict[str, Any]:
        """Behavior: Decide to SPREAD, IGNORE, or COUNTER a narrative."""
        prompt = (
            f"You are {self.name}, a {self.personality} with susceptibility {self.susceptibility}.\n"
            f"Your current beliefs: {self.beliefs}\n"
            f"Recent memory: {self.memory[-5:]}\n"
            f"New signal: {signal_content}\n"
            "Do you: SPREAD, IGNORE, or COUNTER this narrative? Return JSON: {'action': '...', 'reason': '...'}"
        )
        # In implementation, this calls the LLM
        return await llm_fn(prompt)

    async def reflect(self, llm_fn: Callable):
        """Reflection: Periodically summarize memories into core beliefs."""
        if not self.memory:
            return
            
        prompt = (
            "Summarize what you've learned from these social interactions into 3 core beliefs.\n"
            f"MEMORIES:\n" + "\n".join(self.memory[-20:])
        )
        summary = await llm_fn(prompt)
        self.beliefs = summary
