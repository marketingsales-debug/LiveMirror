"""
Noise Robustness — sarcasm, spam, bot detection
Owner: Claude

Rule-based v1: sarcasm detection, spam scoring, organic-vs-manufactured.
Reduces confidence in fusion layer for noisy signals.
"""

import re
from typing import Tuple


class NoiseDetector:
    """Detect noise in signals: sarcasm, spam, bots."""
    
    def __init__(self):
        """Initialize noise detection patterns."""
        # Sarcasm indicators
        self.sarcasm_markers = {
            "yeah right", "sure sure", "oh please", "as if",
            "obviously", "clearly not", "totally not", "absolutely not",
        }
        
        # Spam patterns
        self.spam_patterns = [
            r"(http|https)://\S+",  # Multiple URLs
            r"\b(click|buy|free|limited time|act now)\b",  # Sales language
            r"[\$#]\d+",  # Price tags
            r"!!+|\\?\?+",  # Excessive punctuation
        ]
        
        # Bot patterns
        self.bot_keywords = {
            "bot", "automated", "script", "macro", "spam", "fake",
        }
    
    def is_sarcastic(self, text: str) -> Tuple[bool, float]:
        """
        Detect sarcasm in text.
        
        Returns:
            (is_sarcastic, confidence)
        """
        text_lower = text.lower()
        
        # Check for sarcasm markers
        marker_matches = sum(1 for m in self.sarcasm_markers if m in text_lower)
        
        if marker_matches > 0:
            return True, min(1.0, marker_matches * 0.4)
        
        # Sentiment contradiction detection (simplified)
        # If text contains positive words but ends with "not" or "lol"
        if ("not" in text_lower or "lol" in text_lower) and self._has_positive_sentiment(text_lower):
            return True, 0.6
        
        return False, 0.0
    
    def spam_score(self, text: str, engagement_count: int = 0) -> float:
        """
        Compute spam score (0-1, higher = more spammy).
        
        Returns:
            Spam score
        """
        score = 0.0
        
        # Pattern matching
        for pattern in self.spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.3
        
        # Repetition check
        words = text.split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.5:  # Lots of repetition
                score += 0.4
        
        # Engagement mismatch
        if engagement_count > 1000 and len(text) < 20:
            score += 0.2  # Very short text with huge engagement = suspicious
        
        return min(1.0, score)
    
    def is_manufactured(self, text: str, engagement: dict, url_count: int = 0) -> Tuple[bool, float]:
        """
        Detect manufactured/bot-like signals.
        
        Args:
            text: Signal content
            engagement: Engagement dict (likes, shares, comments, retweets)
            url_count: Number of URLs in text
        
        Returns:
            (is_manufactured, confidence)
        """
        score = 0.0
        
        # Bot keywords
        if any(kw in text.lower() for kw in self.bot_keywords):
            score += 0.5
        
        # Unusual engagement patterns
        likes = engagement.get("likes", 0)
        comments = engagement.get("comments", 0)
        shares = engagement.get("shares", 0)
        
        # Shares without comments (usually automated)
        if shares > 100 and comments < 5:
            score += 0.4
        
        # Massive engagement on empty content
        if likes > 10000 and len(text.strip()) < 10:
            score += 0.5
        
        # Multiple URLs (often spam)
        if url_count > 5:
            score += 0.4
        
        return score > 0.5, min(1.0, score)
    
    def adjust_confidence(self, base_confidence: float, text: str, engagement: dict) -> float:
        """
        Adjust confidence based on noise detection.
        
        Args:
            base_confidence: Original fusion confidence
            text: Signal content
            engagement: Engagement metrics
        
        Returns:
            Adjusted confidence
        """
        # Sarcasm flips sentiment
        is_sarcastic, sarc_conf = self.is_sarcastic(text)
        if is_sarcastic:
            base_confidence *= (1.0 - sarc_conf)
        
        # Spam reduces confidence
        spam = self.spam_score(text, engagement.get("likes", 0))
        base_confidence *= (1.0 - spam * 0.5)
        
        # Manufactured signals get reduced confidence
        is_mfg, mfg_conf = self.is_manufactured(text, engagement)
        if is_mfg:
            base_confidence *= (1.0 - mfg_conf * 0.5)
        
        return max(0.0, min(1.0, base_confidence))
    
    def _has_positive_sentiment(self, text: str) -> bool:
        """Simple positive sentiment check."""
        positive_words = {
            "great", "good", "excellent", "amazing", "awesome",
            "love", "best", "perfect", "beautiful", "wonderful",
        }
        return any(word in text for word in positive_words)
