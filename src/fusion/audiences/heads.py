"""
Multi-Audience Prediction Heads
Owner: Claude

Generates independent predictions for 4 audience segments
with cross-segment consensus scoring.
"""

from typing import Dict, List
import numpy as np

from ..types import (
    AudienceSegment,
    SegmentPrediction,
    MultiAudiencePrediction,
    TemporalState,
)
from .segments import AudienceSegmentPredictor


class MultiAudiencePredictionHead:
    """Prediction head for multiple audiences."""
    
    def __init__(self, segments: List[AudienceSegment]):
        """Initialize with audience segments."""
        self.segments = segments
        self.predictor = AudienceSegmentPredictor(segments)
    
    def predict(
        self,
        fused_embedding: np.ndarray,
        temporal_state: TemporalState,
        platform_signals: Dict[str, float],
    ) -> MultiAudiencePrediction:
        """
        Predict direction for all audience segments.
        
        Args:
            fused_embedding: 384-dim multimodal embedding
            temporal_state: Temporal dynamics
            platform_signals: Platform sentiment scores
        
        Returns:
            MultiAudiencePrediction with per-segment predictions
        """
        from datetime import datetime
        
        multi_pred = MultiAudiencePrediction(timestamp=datetime.now())
        
        # Generate prediction for each segment
        for segment in self.segments:
            seg_pred = self.predictor.predict_segment(
                segment,
                fused_embedding,
                temporal_state,
                platform_signals,
            )
            multi_pred.add_segment_prediction(seg_pred)
        
        return multi_pred
