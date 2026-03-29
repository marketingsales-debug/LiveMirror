"""
Citation Verification Engine.
Ensures quoted text actually exists in the source signals.
"""

from typing import List, Dict, Any
from .schemas import Citation

class CitationVerifier:
    """Verifies that agent citations are truthful and accurate."""

    @staticmethod
    def verify_citations(citations: List[Citation], source_context: str) -> Dict[str, Any]:
        """
        Check if each citation quote exists in the provided context.
        
        Returns:
            {
                "is_valid": bool,
                "verified_count": int,
                "hallucinations": List[str] # Quotes that were not found
            }
        """
        if not citations:
            return {"is_valid": True, "verified_count": 0, "hallucinations": []}

        hallucinations = []
        verified_count = 0

        for cite in citations:
            # Simple string match for MVP. 
            # In Phase 14, we can upgrade to fuzzy/semantic matching.
            if cite.quote.lower() in source_context.lower():
                verified_count += 1
            else:
                hallucinations.append(cite.quote)

        return {
            "is_valid": len(hallucinations) == 0,
            "verified_count": verified_count,
            "hallucinations": hallucinations
        }
