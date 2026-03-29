"""
RARE Reasoning Engine.
Implements Open-Book architecture and Rejection-Sampled Distillation.
"""

from typing import List, Dict, Any, Optional, Callable
import asyncio

class RAREReasoning:
    """Decouples Knowledge from Reasoning."""

    @staticmethod
    def get_open_book_prompt(query: str, context: str) -> str:
        """Force the model to use only provided context."""
        return (
            "SYSTEM: You are a Deep Reasoning Engine. Use ONLY the provided context to answer. "
            "If the answer is not in the context, say 'Insufficient Information'. "
            "DO NOT use your internal weights for market facts.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUERY: {query}"
        )

class ReasoningDistiller:
    """Implements Rejection Sampling for training data generation."""

    def __init__(self, teacher_llm: Callable):
        self.teacher = teacher_llm

    async def distill_reasoning(self, query: str, ground_truth: str, n_samples: int = 3) -> Optional[str]:
        """
        Runs N inference passes and keeps the one that matches ground truth.
        This builds the 'Golden Dataset'.
        """
        tasks = [self.teacher(query) for _ in range(n_samples)]
        results = await asyncio.gather(*tasks)

        for thought_chain in results:
            if ground_truth.lower() in thought_chain.lower():
                return thought_chain # Verified correct logic
        
        return None
