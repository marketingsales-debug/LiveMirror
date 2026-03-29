"""
Unit tests for CrossModalReasoning.
Owner: Claude
"""

import pytest
import numpy as np
from src.fusion.reasoning import CrossModalReasoning

class TestModalityReasoning:
    """Test CrossModalReasoning logic and alignment scoring."""
    
    def test_perfect_alignment(self):
        """Verify alignment score for identical embeddings."""
        reasoning = CrossModalReasoning()
        # Identical 384-dim arrays
        emb = np.random.rand(384).astype(np.float32)
        embeddings = {"text": emb, "audio": emb}
        
        res = reasoning.compute_modality_alignment(embeddings)
        assert res['alignment'] == 1.0
        assert res['conflict'] == 0.0
        assert res['pairwise_count'] == 1
        
    def test_complete_conflict(self):
        """Verify conflict score for opposite embeddings."""
        reasoning = CrossModalReasoning()
        # Opposite 384-dim arrays
        emb1 = np.ones(384).astype(np.float32)
        emb2 = -np.ones(384).astype(np.float32)
        embeddings = {"text": emb1, "audio": emb2}
        
        res = reasoning.compute_modality_alignment(embeddings)
        assert res['alignment'] == 0.0 # Clamped to 0
        assert res['conflict'] == 1.0
        
    def test_confidence_boost_penalty_logic(self):
        """Verify confidence boost and penalty logic."""
        class MockResult:
            def __init__(self, confidence):
                self.consensus_confidence = confidence
                
        reasoning = CrossModalReasoning()
        
        # 1. Boost (high alignment)
        res_high = MockResult(0.5)
        reasoning.final_prediction_with_reasoning(res_high, {'alignment': 0.95, 'conflict': 0.05})
        assert res_high.consensus_confidence > 0.5
        assert res_high.metadata['reasoning']['confidence_multiplier'] > 1.0
        
        # 2. Penalty (high conflict)
        res_low = MockResult(0.5)
        reasoning.final_prediction_with_reasoning(res_low, {'alignment': 0.1, 'conflict': 0.9})
        assert res_low.consensus_confidence < 0.5
        assert res_low.metadata['reasoning']['confidence_multiplier'] < 0.8
        
    def test_detect_modality_conflict_lie(self):
        """Verify detection of specific lies (bullish text + conflict)."""
        reasoning = CrossModalReasoning()
        
        # 1. Bullish text + High conflict
        report_bad = {'conflict': 0.8}
        text_sentiment = 0.9
        res_bad = reasoning.detect_modality_conflict(report_bad, text_sentiment)
        assert res_bad['likely_manipulation'] is True
        
        # 2. Bullish text + Low conflict
        report_good = {'conflict': 0.1}
        res_good = reasoning.detect_modality_conflict(report_good, 0.9)
        assert res_good['likely_manipulation'] is False
