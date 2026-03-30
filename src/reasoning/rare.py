"""
Logical Reasoning Module.
Extracted patterns from RARE (Rejection Sampling) and Z1 (Shifted Thinking).
"""

from typing import Dict, Any, Optional, Callable
import asyncio

class RAREReasoning:
    """Decouples Knowledge from Reasoning."""

    @staticmethod
    def get_open_book_prompt(query: str, context: str) -> str:
        """Force the model to use only provided context (RARE Pattern)."""
        return (
            "You are a REASONING engine, not a KNOWLEDGE engine.\n"
            "- NEVER answer from internal knowledge for facts (prices, dates, names).\n"
            "- ALWAYS use the retrieved context below.\n"
            "- If the context doesn't contain the answer, respond: {'status': 'INSUFFICIENT_DATA'}\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUERY: {query}"
        )

    @staticmethod
    async def rejection_sample(question: str, ground_truth: str, llm_fn: Callable, n: int = 5) -> Optional[str]:
        """Generate N reasoning chains, keep only the one that gets the right answer (RARE Pattern)."""
        tasks = [llm_fn(question) for _ in range(n)]
        chains = await asyncio.gather(*tasks)
        
        # Keep chains that mention the ground truth
        valid = [c for c in chains if ground_truth.lower() in c.lower()]
        if not valid:
            return None
            
        # Return the shortest correct chain (most efficient logic)
        return min(valid, key=len)

class Z1Thinking:
    """Implements two-stage thinking to prevent circular logic."""

    @staticmethod
    async def deep_think(state: Dict[str, Any], llm_fn: Callable) -> Dict[str, Any]:
        """Node 1: Trajectory generation (Z1 Pattern)."""
        prompt = f"Think step by step about this signal. Budget: 2000 tokens.\nContext: {state.get('source_context')}"
        state["trajectory"] = await llm_fn(prompt)
        return state

    @staticmethod
    async def shift_synthesize(state: Dict[str, Any], llm_fn: Callable) -> Dict[str, Any]:
        """Node 2: Forced synthesis (Z1 Pattern)."""
        prompt = (
            "STOP THINKING. Synthesize your trajectory into a single prediction.\n"
            f"TRAJECTORY: {state['trajectory']}\n"
            "Return JSON with direction, confidence, and evidence."
        )
        state["prediction"] = await llm_fn(prompt)
        return state
