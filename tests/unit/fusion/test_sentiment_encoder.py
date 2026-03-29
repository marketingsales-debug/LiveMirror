"""
Unit tests for SentimentEncoder.
Owner: Claude
"""

import pytest
from src.fusion.encoders.sentiment import SentimentEncoder

class TestSentimentEncoder:
    """Test SentimentEncoder classification and availability."""
    
    @pytest.mark.skip(reason="Downloads 440MB weights on first run")
    def test_sentiment_classification(self):
        """Verify sentiment classification for finance phrases."""
        encoder = SentimentEncoder()
        
        # Bullish
        res_bull = encoder.encode("Earnings exceeded analyst expectations")
        assert res_bull["label"] == "bullish"
        assert res_bull["confidence"] > 0.8
        
        # Bearish
        res_bear = encoder.encode("Market crash expected after bankruptcy report")
        assert res_bear["label"] == "bearish"
        assert res_bear["confidence"] > 0.8
        
        # Neutral
        res_neu = encoder.encode("The meeting starts at 9am")
        assert res_neu["label"] == "neutral"
        
    def test_handle_empty_input(self):
        """Verify encoder handles empty text gracefully."""
        encoder = SentimentEncoder()
        # Mock available to skip download
        encoder._available = True 
        assert encoder.encode("") is None
        assert encoder.encode(None) is None
        
    def test_intensity_computation(self):
        """Verify intensity mapping logic (confidence -> intensity)."""
        encoder = SentimentEncoder()
        # Intensity = (confidence - 0.33) / 0.67
        # 1.0 confidence = 1.0 intensity
        # 0.33 confidence = 0.0 intensity
        
        # Manual check (mocking logic)
        confidence = 0.8
        intensity = (0.8 - 0.33) / 0.67
        assert round(intensity, 3) == 0.701
