"""
Audience Segment Predictor
Owner: Claude

4 default segments with platform weights:
- crypto_twitter
- mainstream_media
- retail_investors
- tech_community
"""

import numpy as np
from typing import Dict, List

from ..types import AudienceSegment, SegmentPrediction, TemporalState


class AudienceSegmentPredictor:
    """Predict direction and confidence for each audience segment."""
    
    def __init__(self, segments: List[AudienceSegment]):
        """Initialize with audience segments."""
        self.segments = segments
    
    def predict_segment(
        self,
        segment: AudienceSegment,
        fused_embedding: np.ndarray,
        temporal_state: TemporalState,
        platform_signals: Dict[str, float],
    ) -> SegmentPrediction:
        """
        Predict direction for a specific audience segment.
        
        Args:
            segment: Target audience segment
            fused_embedding: 384-dim fused multimodal embedding
            temporal_state: Temporal dynamics (velocity, momentum)
            platform_signals: Dict of platform -> sentiment score
        
        Returns:
            SegmentPrediction with direction and confidence
        """
        # Compute segment-weighted signal
        weighted_signal = self._compute_weighted_signal(
            segment,
            fused_embedding,
            platform_signals
        )
        
        # Add temporal momentum
        temporal_component = temporal_state.momentum
        
        # Combine: 70% weighted signal, 30% temporal
        combined_signal = (weighted_signal * 0.7) + (temporal_component * 0.1)
        
        # Clamp to [-1, 1]
        direction = np.tanh(combined_signal)
        
        # Confidence: higher momentum = higher confidence
        base_confidence = 0.5 + (abs(temporal_component) * 0.1)
        confidence = min(1.0, max(0.0, base_confidence))
        
        return SegmentPrediction(
            segment_name=segment.name,
            direction=float(direction),
            confidence=float(confidence),
            reasoning=f"Weighted signal={weighted_signal:.3f}, momentum={temporal_component:.3f}",
            modality_contributions={
                "embedding_signal": float(weighted_signal),
                "temporal_momentum": float(temporal_component),
            }
        )
    
    def _compute_weighted_signal(
        self,
        segment: AudienceSegment,
        embedding: np.ndarray,
        platform_signals: Dict[str, float],
    ) -> float:
        """
        Compute segment-weighted signal from platforms and embedding.
        
        Args:
            segment: Audience segment with platform weights
            embedding: 384-dim embedding
            platform_signals: Platform -> sentiment/signal score
        
        Returns:
            Weighted signal in [-1, 1]
        """
        # Platform-weighted signal
        platform_score = 0.0
        total_weight = 0.0
        
        for platform, weight in segment.platform_weights.items():
            if platform in platform_signals:
                platform_score += platform_signals[platform] * weight
                total_weight += weight
        
        if total_weight > 0:
            platform_score = platform_score / total_weight
        
        # Embedding-based signal (use L2 norm as proxy for signal strength)
        embedding_norm = np.linalg.norm(embedding)
        embedding_signal = np.tanh(embedding_norm / 100.0)  # Scale and squash
        
        # Combine 60% platform, 40% embedding
        combined = (platform_score * 0.6) + (embedding_signal * 0.4)
        
        return float(np.clip(combined, -1.0, 1.0))
