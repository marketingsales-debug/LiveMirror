"""
Citation Verification Engine.
Ensures quoted text actually exists in the source signals.
Uses exact match first, then fuzzy matching as fallback.
"""

from typing import List, Dict, Any
from difflib import SequenceMatcher
from .schemas import Citation


class CitationVerifier:
    """Verifies that agent citations are truthful and accurate."""

    FUZZY_THRESHOLD = 0.75  # Minimum similarity ratio for fuzzy match

    @staticmethod
    def _fuzzy_match(quote: str, context: str, threshold: float = 0.75) -> bool:
        """
        Sliding-window fuzzy match over context.
        Catches paraphrased citations that exact match would miss.
        """
        quote_lower = quote.lower()
        context_lower = context.lower()
        quote_words = quote_lower.split()
        context_words = context_lower.split()
        window_size = len(quote_words)

        if window_size == 0 or len(context_words) < window_size:
            return False

        for i in range(len(context_words) - window_size + 1):
            window = " ".join(context_words[i : i + window_size])
            ratio = SequenceMatcher(None, quote_lower, window).ratio()
            if ratio >= threshold:
                return True

        # Also try character-level sliding window for short quotes
        if len(quote_lower) < 100:
            chunk_size = len(quote_lower)
            for i in range(len(context_lower) - chunk_size + 1):
                chunk = context_lower[i : i + chunk_size]
                ratio = SequenceMatcher(None, quote_lower, chunk).ratio()
                if ratio >= threshold:
                    return True

        return False

    @classmethod
    def verify_citations(
        cls, citations: List[Citation], source_context: str
    ) -> Dict[str, Any]:
        """
        Check if each citation quote exists in the provided context.
        Uses exact match first, then fuzzy matching as fallback.

        Returns:
            {
                "is_valid": bool,
                "verified_count": int,
                "hallucinations": List[str],
                "fuzzy_matches": List[str]
            }
        """
        if not citations:
            return {
                "is_valid": True,
                "verified_count": 0,
                "hallucinations": [],
                "fuzzy_matches": [],
            }

        hallucinations = []
        fuzzy_matches = []
        verified_count = 0

        for cite in citations:
            # 1. Exact match (fast path)
            if cite.quote.lower() in source_context.lower():
                verified_count += 1
            # 2. Fuzzy match (fallback for paraphrased citations)
            elif cls._fuzzy_match(cite.quote, source_context, cls.FUZZY_THRESHOLD):
                verified_count += 1
                fuzzy_matches.append(cite.quote)
            else:
                hallucinations.append(cite.quote)

        return {
            "is_valid": len(hallucinations) == 0,
            "verified_count": verified_count,
            "hallucinations": hallucinations,
            "fuzzy_matches": fuzzy_matches,
        }
