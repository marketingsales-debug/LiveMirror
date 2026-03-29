"""
Unit tests for audience segment prediction.
Owner: Claude
"""

import pytest
import numpy as np
from datetime import datetime
from src.fusion.types import AudienceSegment, TemporalState
from src.fusion.audiences.segments import AudienceSegmentPredictor
from src.fusion.audiences.heads import MultiAudiencePredictionHead


class TestAudienceSegmentPredictor:
    """Test segment prediction."""
    
    def test_predict_segment(self):
        """Generate prediction for a segment."""
        segment = AudienceSegment(
            name="crypto_twitter",
            platform_weights={"twitter": 0.8, "reddit": 0.2}
        )
        
        predictor = AudienceSegmentPredictor([segment])
        
        embedding = np.random.randn(384).astype(np.float32)
        vel = np.random.randn(384).astype(np.float32)
        acc = np.random.randn(384).astype(np.float32)
        temporal = TemporalState(
            timestamp=datetime.now(),
            embedding=embedding,
            velocity=vel,
            acceleration=acc,
        )
        
        platform_signals = {"twitter": 0.5, "reddit": 0.3}
        
        pred = predictor.predict_segment(segment, embedding, temporal, platform_signals)
        
        assert pred.segment_name == "crypto_twitter"
        assert -1.0 <= pred.direction <= 1.0
        assert 0.0 <= pred.confidence <= 1.0


class TestMultiAudiencePredictionHead:
    """Test multi-audience predictions."""
    
    def test_predict_all_segments(self):
        """Generate predictions for all segments."""
        segments = [
            AudienceSegment(
                name="crypto_twitter",
                platform_weights={"twitter": 1.0}
            ),
            AudienceSegment(
                name="mainstream_media",
                platform_weights={"news": 1.0}
            ),
        ]
        
        head = MultiAudiencePredictionHead(segments)
        
        embedding = np.random.randn(384).astype(np.float32)
        vel = np.random.randn(384).astype(np.float32)
        acc = np.random.randn(384).astype(np.float32)
        temporal = TemporalState(
            timestamp=datetime.now(),
            embedding=embedding,
            velocity=vel,
            acceleration=acc,
        )
        
        platform_signals = {"twitter": 0.5, "news": 0.3}
        
        multi_pred = head.predict(embedding, temporal, platform_signals)
        
        assert len(multi_pred.segment_predictions) == 2
        assert multi_pred.consensus_direction != 0.0
        assert 0.0 <= multi_pred.consensus_confidence <= 1.0
