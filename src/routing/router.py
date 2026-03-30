"""
Economic Model Router.
Routes tasks to local vs. frontier models based on signal complexity.
Includes prompt optimization via DSPy-style few-shot selection.
"""

from typing import Dict, Any, List
from difflib import SequenceMatcher


class ModelRouter:
    """Saves 50% on API costs by routing simple tasks to local models."""

    COMPLEX_KEYWORDS = frozenset([
        "analyze", "reason", "compare", "evaluate", "debate", "conflict",
        "synthesize", "predict", "correlate", "causal", "backtest",
    ])

    @staticmethod
    def compute_complexity(query: str) -> float:
        """
        Return a 0-1 complexity score combining length, keyword density,
        and structural markers (questions, enumerations).
        """
        words = query.lower().split()
        word_count = len(words)
        if word_count == 0:
            return 0.0

        keyword_hits = sum(1 for w in words if w in ModelRouter.COMPLEX_KEYWORDS)
        keyword_density = keyword_hits / word_count

        has_question = "?" in query
        has_enumeration = any(c in query for c in ["\n-", "\n*", "\n1."])

        # Weighted score
        length_score = min(word_count / 100.0, 1.0)
        struct_bonus = 0.1 * has_question + 0.1 * has_enumeration
        score = 0.4 * length_score + 0.4 * keyword_density + 0.2 * struct_bonus
        return min(score, 1.0)

    @classmethod
    def get_optimal_model(cls, query: str, complexity_threshold: float = 0.3) -> str:
        """
        Route to frontier or local model based on computed complexity.
        Returns model identifier string.
        """
        score = cls.compute_complexity(query)
        if score >= complexity_threshold:
            return "gpt-4o"
        return "phi-4-local"


class PromptOptimizer:
    """Auto few-shot example selection (DSPy Pattern) with similarity search."""

    def __init__(self, max_examples: int = 200):
        self.examples: List[Dict[str, Any]] = []
        self._max = max_examples

    def record_example(self, input_text: str, output_text: str, score: float):
        """Save a high-quality interaction for future few-shotting."""
        self.examples.append({
            "input": input_text,
            "output": output_text,
            "score": score,
        })
        # FIFO eviction
        if len(self.examples) > self._max:
            self.examples = self.examples[-self._max:]

    def get_best_examples(self, query: str, k: int = 2) -> str:
        """
        Find the most relevant *and* highest scoring examples.
        Uses token-overlap similarity weighted by quality score.
        """
        if not self.examples:
            return ""

        query_lower = query.lower()
        scored = []
        for ex in self.examples:
            sim = SequenceMatcher(None, query_lower, ex["input"].lower()).ratio()
            # Blend similarity (60%) with quality score (40%)
            combined = 0.6 * sim + 0.4 * ex["score"]
            scored.append((combined, ex))

        scored.sort(key=lambda t: t[0], reverse=True)
        top = [ex for _, ex in scored[:k]]

        few_shot = "Here are examples of successful reasoning:\n"
        for ex in top:
            few_shot += f"INPUT: {ex['input']}\nOUTPUT: {ex['output']}\n---\n"
        return few_shot
