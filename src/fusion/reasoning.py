"""
Cross-Modal Reasoning Engine.
Owner: Claude

Detects conflicts and alignment between Text, Audio, Video, and Sentiment modalities.
Applies confidence penalties to "lying" signals (high conflict).
"""

import torch
import numpy as np
from typing import Dict, List, Any, Optional


class CrossModalReasoning:
    """Detect conflicts and alignment between modalities."""
    
    def compute_modality_alignment(self, embeddings_dict: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Score how well all modalities agree using pairwise cosine similarity.
        
        Args:
            embeddings_dict: Dict of modality name to 384-dim embedding
            
        Returns:
            Alignment and conflict scores (0.0 to 1.0)
        """
        modalities = list(embeddings_dict.keys())
        
        if len(modalities) < 2:
            return {
                'alignment': 1.0, 
                'conflict': 0.0, 
                'modalities_used': modalities
            }
            
        # 1. Compute pairwise cosine similarity
        similarities = []
        for i, mod1 in enumerate(modalities):
            for mod2 in modalities[i+1:]:
                # Convert to torch for similarity computation
                v1 = torch.from_numpy(embeddings_dict[mod1]).unsqueeze(0)
                v2 = torch.from_numpy(embeddings_dict[mod2]).unsqueeze(0)
                
                sim = torch.nn.functional.cosine_similarity(v1, v2).item()
                similarities.append(sim)
                
        # 2. Compute aggregated scores
        alignment = np.mean(similarities) if similarities else 1.0
        # Alignment can be negative (opposite vectors), we clamp to 0-1
        alignment = max(0.0, min(1.0, alignment))
        conflict = 1.0 - alignment
        
        return {
            'alignment': round(float(alignment), 3),
            'conflict': round(float(conflict), 3),
            'modalities_used': modalities,
            'pairwise_count': len(similarities)
        }
        
    def detect_modality_conflict(self, alignment_report: Dict[str, Any], text_sentiment: float) -> Optional[Dict[str, Any]]:
        """
        Heuristic check for specific multi-modal lies.
        Example: Text is bullish (+0.8) but overall alignment is very low (<0.3).
        """
        conflict = alignment_report.get('conflict', 0.0)
        
        if text_sentiment > 0.7 and conflict > 0.6:
            return {
                'likely_manipulation': True,
                'confidence': 0.85,
                'type': 'high_sentiment_low_alignment_conflict',
                'reason': f"Bullish text ({text_sentiment}) has high conflict ({conflict}) with other modalities"
            }
            
        return {'likely_manipulation': False, 'confidence': 0.0}
        
    def final_prediction_with_reasoning(self, base_result: Any, alignment_report: Dict[str, Any]) -> Any:
        """
        Adjust prediction confidence based on alignment.
        
        Rules:
        - High Alignment (>0.8): Up to 20% confidence boost.
        - High Conflict (>0.6): Up to 30% confidence penalty.
        """
        alignment = alignment_report['alignment']
        conflict = alignment_report['conflict']
        
        # 1. Calculate multiplier
        multiplier = 1.0
        if alignment > 0.8:
            multiplier += (alignment - 0.8) * 1.0  # Max +0.2 boost
        elif conflict > 0.6:
            multiplier -= (conflict - 0.4) * 0.5  # Max -0.3 penalty
            
        multiplier = max(0.4, min(1.2, multiplier)) # Clamp
        
        # 2. Apply to result
        # Note: base_result is expected to be a MultiAudiencePrediction or similar
        if hasattr(base_result, 'consensus_confidence'):
            base_result.consensus_confidence *= multiplier
            # Cap at 0.99
            base_result.consensus_confidence = min(0.99, base_result.consensus_confidence)
            
        # Add reasoning metadata
        if not hasattr(base_result, 'metadata'):
            base_result.metadata = {}
        base_result.metadata['reasoning'] = {
            'alignment': alignment,
            'conflict': conflict,
            'confidence_multiplier': round(float(multiplier), 3)
        }
        
        return base_result
