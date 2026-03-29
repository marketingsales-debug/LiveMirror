"""
Delta Signal Analysis.
Calculates 'Emotional Acceleration' to predict narrative tipping points.
"""

from typing import List, Dict

class DeltaAnalyzer:
    """Moves from static sentiment to narrative velocity/acceleration."""

    @staticmethod
    def calculate_emotional_delta(sentiment_history: List[float], time_window_min: int = 5) -> Dict[str, float]:
        """
        Analyzes the change in sentiment over time.
        Positive acceleration = high risk of narrative breakout (FOMO).
        Negative acceleration = high risk of narrative collapse (Panic).
        """
        if len(sentiment_history) < 2:
            return {"velocity": 0.0, "acceleration": 0.0}

        # Calculate Velocity (v = ds/dt)
        v1 = sentiment_history[-1] - sentiment_history[-2]
        
        if len(sentiment_history) < 3:
            return {"velocity": round(v1, 3), "acceleration": 0.0}

        # Calculate Acceleration (a = dv/dt)
        v0 = sentiment_history[-2] - sentiment_history[-3]
        acceleration = v1 - v0

        return {
            "velocity": round(v1, 3),
            "acceleration": round(acceleration, 3)
        }
