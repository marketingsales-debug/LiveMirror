from typing import Dict, Any, List
from src.shared.types.platform import Platform

class SentimentAnalyzer:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def analyze(self, text: str, platform: Platform, context: Dict[str, Any] = None) -> float:
        """
        Scores text sentiment from -1.0 (extremely negative) to 1.0 (extremely positive).
        Platform-specific nuances are applied here.
        """
        # A basic heuristic mock for now. In a real system, this would call Qwen or VADER.
        lower_text = text.lower()
        score = 0.0
        
        positive_words = {"good", "great", "excellent", "love", "support", "agree", "bullish"}
        negative_words = {"bad", "terrible", "hate", "oppose", "disagree", "bearish", "crash"}
        
        words = set(lower_text.split())
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        
        if pos_count == 0 and neg_count == 0:
            base_score = 0.0
        else:
            base_score = (pos_count - neg_count) / (pos_count + neg_count)
            
        # Apply platform specific cultural weights
        if platform == Platform.REDDIT:
            # Reddit tends to be more extreme / echo-chambered
            return max(-1.0, min(1.0, base_score * 1.2))
        elif platform == Platform.TWITTER:
            # Twitter tends to skew negative due to dunking dynamics
            return max(-1.0, min(1.0, base_score - 0.1))
            
        return max(-1.0, min(1.0, base_score))
        
    def batch_analyze(self, contents: List[str], platforms: List[Platform]) -> List[float]:
        return [self.analyze(content, platform) for content, platform in zip(contents, platforms)]
