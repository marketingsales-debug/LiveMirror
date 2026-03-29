"""
Unit tests for NoiseDetector.
Owner: Claude
"""

import pytest
from src.fusion.noise import NoiseDetector


class TestNoiseDetector:
    """Test noise detection."""
    
    def test_sarcasm_detection_markers(self):
        """Detect sarcasm from markers."""
        detector = NoiseDetector()
        
        is_sarc, conf = detector.is_sarcastic("Yeah right, Bitcoin is totally dead")
        assert is_sarc is True
        assert conf > 0.0
    
    def test_sarcasm_not_detected_normal(self):
        """Normal text not flagged as sarcastic."""
        detector = NoiseDetector()
        
        is_sarc, conf = detector.is_sarcastic("Bitcoin rally continues")
        assert is_sarc is False
        assert conf == 0.0
    
    def test_spam_score_high_for_suspicious(self):
        """Suspicious content gets high spam score."""
        detector = NoiseDetector()
        
        text = "Click here for FREE Bitcoin!!! http://spam.com amazing deal!!!!"
        score = detector.spam_score(text)
        assert score > 0.5
    
    def test_spam_score_low_for_normal(self):
        """Normal text gets low spam score."""
        detector = NoiseDetector()
        
        text = "Ethereum price analysis for today"
        score = detector.spam_score(text)
        assert score < 0.3
    
    def test_manufactured_detection(self):
        """Detect manufactured signals."""
        detector = NoiseDetector()
        
        text = "Check this out! bot automated script"
        engagement = {"likes": 50000, "comments": 2, "shares": 1000}
        
        is_mfg, conf = detector.is_manufactured(text, engagement, url_count=0)
        assert is_mfg is True
        assert conf > 0.0
    
    def test_confidence_adjustment(self):
        """Confidence is adjusted for noise."""
        detector = NoiseDetector()
        
        text = "Yeah right, Bitcoin is amazing!!! Click here"
        engagement = {"likes": 100, "comments": 1, "shares": 50}
        
        original = 0.9
        adjusted = detector.adjust_confidence(original, text, engagement)
        
        assert adjusted < original
        assert 0.0 <= adjusted <= 1.0
