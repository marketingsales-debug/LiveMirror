from datetime import datetime, timedelta
from typing import List, Dict

class EmotionalContagionTracker:
    def __init__(self, tipping_point_threshold: float = 0.4):
        self.tipping_point_threshold = tipping_point_threshold
        self.sentiment_history: List[Dict[str, any]] = []

    def record_sentiment(self, text_id: str, platform: str, sentiment_score: float, timestamp: datetime):
        self.sentiment_history.append({
            "id": text_id,
            "platform": platform,
            "score": sentiment_score,
            "timestamp": timestamp
        })
        
    def calculate_emotional_velocity(self, window_hours: int = 1) -> float:
        """
        Calculates the rate of change of sentiment over the given time window.
        Returns velocity: positive means getting more positive, negative means getting angrier/more negative.
        """
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent = [x for x in self.sentiment_history if x["timestamp"] >= cutoff]
        
        if len(recent) < 2:
            return 0.0
            
        recent.sort(key=lambda x: x["timestamp"])
        first_half = recent[:len(recent)//2]
        second_half = recent[len(recent)//2:]
        
        if not first_half or not second_half:
            return 0.0
            
        avg_first = sum(x["score"] for x in first_half) / len(first_half)
        avg_second = sum(x["score"] for x in second_half) / len(second_half)
        
        # Velocity is the difference across the time blocks
        return avg_second - avg_first

    def detect_tipping_point(self, current_velocity: float) -> bool:
        """
        Detects if current emotional velocity exceeds the threshold, signaling an incoming cascade.
        """
        return abs(current_velocity) >= self.tipping_point_threshold
