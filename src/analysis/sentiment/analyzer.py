"""
SentimentAnalyzer — Multi-platform text sentiment scoring.
Returns a value from -1.0 (extremely negative) to 1.0 (extremely positive).

Fixes applied per Claude's adversarial review:
  - Punctuation stripping before word matching
  - Negation handling ("not good", "doesn't work", "can't support", etc.)
  - Expanded vocabulary with crypto, financial, and social slang terms
"""

import re
from typing import Dict, List, Optional
from src.shared.types.platform import Platform


# ---------------------------------------------------------------------------
# Vocabulary banks
# ---------------------------------------------------------------------------

POSITIVE_WORDS = {
    # General
    "good", "great", "excellent", "love", "support", "agree", "amazing",
    "fantastic", "wonderful", "outstanding", "brilliant", "perfect", "best",
    "helpful", "impressive", "solid", "reliable", "innovative", "clean",
    # Financial / Econ
    "bullish", "rally", "surge", "moon", "pump", "profit", "growth",
    "undervalued", "recovery", "breakout", "uptrend", "buy", "long",
    # Crypto slang
    "gm", "wagmi", "ngmi", "lfg", "hodl", "ath", "rekt", "alpha",
    "based", "gigachad", "degen", "ape", "diamond", "hands",
    # Social approval
    "win", "winning", "epic", "fire", "goat", "king", "queen",
    "banger", "slaps", "heat", "w",
}

NEGATIVE_WORDS = {
    # General
    "bad", "terrible", "hate", "oppose", "disagree", "awful", "horrible",
    "dreadful", "disgusting", "pathetic", "useless", "broken", "wrong",
    "failed", "failure", "trash", "garbage", "waste",
    # Financial / Econ
    "bearish", "crash", "dump", "sell", "short", "overvalued", "bubble",
    "collapse", "recession", "correction", "downtrend", "loss",
    # Crypto slang  
    "rug", "scam", "ponzi", "shill", "fud", "rekt", "exit", "exploit",
    # Social disapproval
    "cringe", "mid", "l", "ratio", "clown", "sus", "cap",
}

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "don't", "doesn't",
    "didn't", "won't", "wouldn't", "can't", "cannot", "isn't", "isn't",
    "aren't", "wasn't", "weren't", "hasn't", "haven't", "hardly",
    "barely", "scarcely",
}

# Platform-specific multipliers
PLATFORM_WEIGHTS: Dict[Platform, float] = {
    Platform.REDDIT:     1.2,   # Echo-chamber amplification
    Platform.TWITTER:   -0.1,   # Skews negative from dunking culture
    Platform.TIKTOK:     0.05,  # Slightly positive by default
    Platform.BLUESKY:    0.0,
    Platform.YOUTUBE:    0.05,
    Platform.HACKERNEWS:-0.05,  # Skeptical community
    Platform.POLYMARKET: 0.0,
    Platform.INSTAGRAM:  0.05,
    Platform.WEB:        0.0,
    Platform.NEWS:      -0.05,
}


def _tokenize(text: str) -> List[str]:
    """Strip punctuation and lowercase."""
    cleaned = re.sub(r"[^\w\s']", " ", text.lower())
    return cleaned.split()


def _score_with_negation(tokens: List[str]) -> float:
    """
    Walk tokens left-to-right. A negation word flips the polarity
    of the next sentiment-bearing word it encounters (within a window of 3).
    """
    score = 0.0
    negation_active = 0  # countdown: how many tokens the negation is still active

    for token in tokens:
        if token in NEGATION_WORDS:
            negation_active = 3  # affect next 3 tokens
            continue

        word_score = 0.0
        if token in POSITIVE_WORDS:
            word_score = 1.0
        elif token in NEGATIVE_WORDS:
            word_score = -1.0

        if word_score != 0.0:
            if negation_active > 0:
                word_score = -word_score
            score += word_score

        if negation_active > 0:
            negation_active -= 1

    return score


class SentimentAnalyzer:
    """
    Scores text sentiment on a -1 to 1 scale with platform-specific adjustments.

    Args:
        use_llm: Reserved for future LLM-backed scoring once the ingestion
                 API layer is available from Claude's backend.
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def analyze(
        self,
        text: str,
        platform: Platform,
        context: Optional[Dict] = None,
    ) -> float:
        """
        Returns a float in [-1.0, 1.0].
        """
        tokens = _tokenize(text)
        if not tokens:
            return 0.0

        raw_score = _score_with_negation(tokens)

        # Normalise by token count so long texts don't dwarf short ones
        normalised = raw_score / max(len(tokens), 1)

        # Apply platform bias offset and clamp
        bias = PLATFORM_WEIGHTS.get(platform, 0.0)
        final = normalised + bias

        return max(-1.0, min(1.0, final))

    def batch_analyze(
        self,
        contents: List[str],
        platforms: List[Platform],
    ) -> List[float]:
        return [
            self.analyze(c, p)
            for c, p in zip(contents, platforms)
        ]
