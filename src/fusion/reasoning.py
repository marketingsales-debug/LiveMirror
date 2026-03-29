"""
Cross-Modal Reasoning Engine.
Owner: Claude

Detects conflicts and alignment between Text, Audio, Video, and Sentiment modalities.
Applies confidence penalties to "lying" signals (high conflict).
Surfaces specific conflict patterns: deception, inconsistency, uncertainty.
"""

import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ConflictType(Enum):
    """Types of cross-modal conflicts."""
    NONE = "none"
    DECEPTION = "deception"  # Intentional mismatch (bullish words + nervous tone)
    INCONSISTENCY = "inconsistency"  # Unintentional mismatch (mixed signals)
    UNCERTAINTY = "uncertainty"  # Low confidence across modalities
    MANIPULATION = "manipulation"  # Coordinated misleading signals


@dataclass
class PairwiseConflict:
    """Conflict between two specific modalities."""
    modality_a: str
    modality_b: str
    similarity: float
    conflict_score: float
    conflict_type: ConflictType
    description: str


@dataclass
class CrossModalConflictReport:
    """Comprehensive cross-modal conflict analysis."""
    overall_alignment: float
    overall_conflict: float
    pairwise_conflicts: List[PairwiseConflict]
    dominant_conflict_type: ConflictType
    manipulation_risk: float
    confidence_penalty: float
    modalities_analyzed: List[str]
    reasoning: str


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class CrossModalReasoning:
    """Detect conflicts and alignment between modalities."""
    
    # Modality reliability weights (higher = more trustworthy)
    MODALITY_WEIGHTS = {
        "text": 0.3,
        "audio": 0.25,
        "video": 0.25,
        "sentiment": 0.2,
    }
    
    # Conflict thresholds
    HIGH_CONFLICT_THRESHOLD = 0.6
    MEDIUM_CONFLICT_THRESHOLD = 0.4
    DECEPTION_THRESHOLD = 0.7
    
    def __init__(self):
        """Initialize reasoning engine."""
        pass
    
    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        t1 = torch.from_numpy(v1.astype(np.float32)).unsqueeze(0)
        t2 = torch.from_numpy(v2.astype(np.float32)).unsqueeze(0)
        return torch.nn.functional.cosine_similarity(t1, t2).item()
    
    def _classify_pairwise_conflict(
        self,
        mod_a: str,
        mod_b: str,
        similarity: float,
        sentiment_data: Optional[Dict[str, float]] = None,
    ) -> Tuple[ConflictType, str]:
        """
        Classify the type of conflict between two modalities.
        
        Returns:
            (ConflictType, description)
        """
        conflict_score = 1.0 - _clamp(similarity)
        
        if conflict_score < self.MEDIUM_CONFLICT_THRESHOLD:
            return ConflictType.NONE, "Modalities are aligned"
        
        # Specific conflict patterns
        pair = frozenset([mod_a, mod_b])
        
        # Text vs Audio: bullish words + nervous/hesitant tone
        if pair == frozenset(["text", "audio"]):
            if conflict_score >= self.DECEPTION_THRESHOLD:
                return ConflictType.DECEPTION, "Text sentiment contradicts vocal tone/prosody"
            return ConflictType.INCONSISTENCY, "Mild mismatch between words and vocal delivery"
        
        # Text vs Video: confident words + hesitant body language
        if pair == frozenset(["text", "video"]):
            if conflict_score >= self.DECEPTION_THRESHOLD:
                return ConflictType.DECEPTION, "Text sentiment contradicts visual cues/body language"
            return ConflictType.INCONSISTENCY, "Mild mismatch between words and visual presentation"
        
        # Audio vs Video: voice confidence vs body language
        if pair == frozenset(["audio", "video"]):
            if conflict_score >= self.DECEPTION_THRESHOLD:
                return ConflictType.MANIPULATION, "Vocal confidence contradicts body language"
            return ConflictType.UNCERTAINTY, "Uncertain delivery across audio and video"
        
        # Sentiment vs others: FinBERT sentiment vs raw modality
        if "sentiment" in pair:
            other = (pair - {"sentiment"}).pop()
            if conflict_score >= self.HIGH_CONFLICT_THRESHOLD:
                return ConflictType.INCONSISTENCY, f"FinBERT sentiment conflicts with {other} embedding"
            return ConflictType.UNCERTAINTY, f"Minor sentiment-{other} divergence"
        
        # Default
        if conflict_score >= self.HIGH_CONFLICT_THRESHOLD:
            return ConflictType.INCONSISTENCY, f"High conflict between {mod_a} and {mod_b}"
        return ConflictType.UNCERTAINTY, f"Moderate uncertainty between {mod_a} and {mod_b}"
    
    def compute_pairwise_conflicts(
        self,
        embeddings_dict: Dict[str, np.ndarray],
        sentiment_data: Optional[Dict[str, float]] = None,
    ) -> List[PairwiseConflict]:
        """
        Compute detailed pairwise conflicts between all modality pairs.
        
        Args:
            embeddings_dict: Dict of modality name to 384-dim embedding
            sentiment_data: Optional dict with sentiment scores per modality
            
        Returns:
            List of PairwiseConflict objects
        """
        modalities = list(embeddings_dict.keys())
        conflicts = []
        
        for i, mod_a in enumerate(modalities):
            for mod_b in modalities[i + 1:]:
                similarity = self._cosine_similarity(
                    embeddings_dict[mod_a],
                    embeddings_dict[mod_b]
                )
                conflict_score = 1.0 - _clamp(similarity)
                conflict_type, description = self._classify_pairwise_conflict(
                    mod_a, mod_b, similarity, sentiment_data
                )
                
                conflicts.append(PairwiseConflict(
                    modality_a=mod_a,
                    modality_b=mod_b,
                    similarity=round(similarity, 3),
                    conflict_score=round(conflict_score, 3),
                    conflict_type=conflict_type,
                    description=description,
                ))
        
        return conflicts
    
    def compute_modality_alignment(self, embeddings_dict: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Score how well all modalities agree using weighted pairwise cosine similarity.
        
        Args:
            embeddings_dict: Dict of modality name to 384-dim embedding
            
        Returns:
            Alignment and conflict scores (0.0 to 1.0) with pairwise breakdown
        """
        modalities = list(embeddings_dict.keys())
        
        if len(modalities) < 2:
            return {
                'alignment': 1.0,
                'conflict': 0.0,
                'modalities_used': modalities,
                'pairwise_conflicts': [],
            }
        
        # Compute pairwise conflicts
        pairwise = self.compute_pairwise_conflicts(embeddings_dict)
        
        # Weighted average alignment
        total_weight = 0.0
        weighted_sim = 0.0
        
        for pc in pairwise:
            w_a = self.MODALITY_WEIGHTS.get(pc.modality_a, 0.25)
            w_b = self.MODALITY_WEIGHTS.get(pc.modality_b, 0.25)
            pair_weight = w_a * w_b
            weighted_sim += pc.similarity * pair_weight
            total_weight += pair_weight
        
        alignment = weighted_sim / total_weight if total_weight > 0 else 1.0
        alignment = _clamp(alignment)
        conflict = 1.0 - alignment
        
        return {
            'alignment': round(alignment, 3),
            'conflict': round(conflict, 3),
            'modalities_used': modalities,
            'pairwise_count': len(pairwise),
            'pairwise_conflicts': [
                {
                    'pair': f"{pc.modality_a}-{pc.modality_b}",
                    'similarity': pc.similarity,
                    'conflict': pc.conflict_score,
                    'type': pc.conflict_type.value,
                    'description': pc.description,
                }
                for pc in pairwise
            ],
        }
    
    def analyze_cross_modal_conflict(
        self,
        embeddings_dict: Dict[str, np.ndarray],
        text_sentiment: Optional[float] = None,
        sentiment_data: Optional[Dict[str, float]] = None,
    ) -> CrossModalConflictReport:
        """
        Comprehensive cross-modal conflict analysis.
        
        Args:
            embeddings_dict: Dict of modality name to 384-dim embedding
            text_sentiment: Optional text sentiment score (-1 to 1)
            sentiment_data: Optional dict with sentiment scores per modality
            
        Returns:
            CrossModalConflictReport with full analysis
        """
        modalities = list(embeddings_dict.keys())
        
        if len(modalities) < 2:
            return CrossModalConflictReport(
                overall_alignment=1.0,
                overall_conflict=0.0,
                pairwise_conflicts=[],
                dominant_conflict_type=ConflictType.NONE,
                manipulation_risk=0.0,
                confidence_penalty=0.0,
                modalities_analyzed=modalities,
                reasoning="Single modality - no cross-modal analysis possible",
            )
        
        # Compute pairwise conflicts
        pairwise = self.compute_pairwise_conflicts(embeddings_dict, sentiment_data)
        
        # Compute weighted alignment
        alignment_report = self.compute_modality_alignment(embeddings_dict)
        overall_alignment = alignment_report['alignment']
        overall_conflict = alignment_report['conflict']
        
        # Determine dominant conflict type
        conflict_types = [pc.conflict_type for pc in pairwise if pc.conflict_type != ConflictType.NONE]
        if not conflict_types:
            dominant_type = ConflictType.NONE
        else:
            # Priority: MANIPULATION > DECEPTION > INCONSISTENCY > UNCERTAINTY
            priority = [ConflictType.MANIPULATION, ConflictType.DECEPTION, 
                       ConflictType.INCONSISTENCY, ConflictType.UNCERTAINTY]
            for ct in priority:
                if ct in conflict_types:
                    dominant_type = ct
                    break
            else:
                dominant_type = ConflictType.UNCERTAINTY
        
        # Compute manipulation risk
        manipulation_risk = 0.0
        if dominant_type == ConflictType.MANIPULATION:
            manipulation_risk = 0.9
        elif dominant_type == ConflictType.DECEPTION:
            manipulation_risk = 0.7
        elif text_sentiment is not None and text_sentiment > 0.7 and overall_conflict > 0.5:
            manipulation_risk = 0.6
        elif overall_conflict > self.HIGH_CONFLICT_THRESHOLD:
            manipulation_risk = 0.4
        
        # Compute confidence penalty
        confidence_penalty = 0.0
        if overall_conflict > self.HIGH_CONFLICT_THRESHOLD:
            confidence_penalty = min(0.4, (overall_conflict - 0.4) * 0.6)
        elif overall_conflict > self.MEDIUM_CONFLICT_THRESHOLD:
            confidence_penalty = (overall_conflict - 0.3) * 0.3
        
        # Generate reasoning
        reasoning_parts = []
        if dominant_type == ConflictType.NONE:
            reasoning_parts.append(f"All {len(modalities)} modalities are well-aligned")
        else:
            high_conflict_pairs = [pc for pc in pairwise if pc.conflict_score >= self.HIGH_CONFLICT_THRESHOLD]
            if high_conflict_pairs:
                pairs_str = ", ".join([f"{pc.modality_a}-{pc.modality_b}" for pc in high_conflict_pairs])
                reasoning_parts.append(f"High conflict detected in: {pairs_str}")
            reasoning_parts.append(f"Dominant conflict type: {dominant_type.value}")
        
        if manipulation_risk > 0.5:
            reasoning_parts.append(f"Elevated manipulation risk ({manipulation_risk:.0%})")
        
        return CrossModalConflictReport(
            overall_alignment=round(overall_alignment, 3),
            overall_conflict=round(overall_conflict, 3),
            pairwise_conflicts=pairwise,
            dominant_conflict_type=dominant_type,
            manipulation_risk=round(manipulation_risk, 3),
            confidence_penalty=round(confidence_penalty, 3),
            modalities_analyzed=modalities,
            reasoning="; ".join(reasoning_parts),
        )
    
    def detect_modality_conflict(
        self,
        alignment_report: Dict[str, Any],
        text_sentiment: float,
    ) -> Dict[str, Any]:
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
        
        if text_sentiment < -0.7 and conflict > 0.6:
            return {
                'likely_manipulation': True,
                'confidence': 0.75,
                'type': 'bearish_text_conflict',
                'reason': f"Bearish text ({text_sentiment}) conflicts with other modalities ({conflict})"
            }
        
        return {'likely_manipulation': False, 'confidence': 0.0}
    
    def final_prediction_with_reasoning(
        self,
        base_result: Any,
        alignment_report: Dict[str, Any],
    ) -> Any:
        """
        Adjust prediction confidence based on alignment.
        
        Rules:
        - High Alignment (>0.8): Up to 20% confidence boost.
        - High Conflict (>0.6): Up to 30% confidence penalty.
        """
        alignment = alignment_report['alignment']
        conflict = alignment_report['conflict']
        
        # Calculate multiplier
        multiplier = 1.0
        if alignment > 0.8:
            multiplier += (alignment - 0.8) * 1.0  # Max +0.2 boost
        elif conflict > 0.6:
            multiplier -= (conflict - 0.4) * 0.5  # Max -0.3 penalty
        
        multiplier = _clamp(multiplier, 0.4, 1.2)
        
        # Apply to result
        if hasattr(base_result, 'consensus_confidence'):
            base_result.consensus_confidence *= multiplier
            base_result.consensus_confidence = min(0.99, base_result.consensus_confidence)
        
        # Add reasoning metadata
        if not hasattr(base_result, 'metadata'):
            base_result.metadata = {}
        
        base_result.metadata['reasoning'] = {
            'alignment': alignment,
            'conflict': conflict,
            'confidence_multiplier': round(multiplier, 3),
            'pairwise_conflicts': alignment_report.get('pairwise_conflicts', []),
        }
        
        return base_result
    
    def detect_ceo_deception_pattern(
        self,
        text_embedding: np.ndarray,
        audio_embedding: Optional[np.ndarray] = None,
        video_embedding: Optional[np.ndarray] = None,
        text_sentiment: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Specific detector for CEO-style deception: bullish words + nervous delivery.
        
        This catches scenarios like earnings calls where the CEO says positive things
        but their voice/body language suggests doubt.
        
        Args:
            text_embedding: Text embedding (required)
            audio_embedding: Audio embedding (optional)
            video_embedding: Video embedding (optional)
            text_sentiment: Sentiment score from text (-1 to 1)
            
        Returns:
            Deception analysis with confidence and reasoning
        """
        result = {
            'deception_detected': False,
            'confidence': 0.0,
            'pattern': None,
            'reasoning': '',
        }
        
        # Need at least text + one other modality
        if audio_embedding is None and video_embedding is None:
            result['reasoning'] = "Insufficient modalities for deception detection"
            return result
        
        # Check text-audio conflict
        if audio_embedding is not None:
            text_audio_sim = self._cosine_similarity(text_embedding, audio_embedding)
            text_audio_conflict = 1.0 - _clamp(text_audio_sim)
            
            if text_sentiment > 0.5 and text_audio_conflict > self.DECEPTION_THRESHOLD:
                result['deception_detected'] = True
                result['confidence'] = 0.75 + (text_audio_conflict - 0.7) * 0.5
                result['pattern'] = 'bullish_words_nervous_tone'
                result['reasoning'] = f"Bullish text (sentiment={text_sentiment:.2f}) conflicts with audio (conflict={text_audio_conflict:.2f})"
                return result
        
        # Check text-video conflict
        if video_embedding is not None:
            text_video_sim = self._cosine_similarity(text_embedding, video_embedding)
            text_video_conflict = 1.0 - _clamp(text_video_sim)
            
            if text_sentiment > 0.5 and text_video_conflict > self.DECEPTION_THRESHOLD:
                result['deception_detected'] = True
                result['confidence'] = 0.70 + (text_video_conflict - 0.7) * 0.4
                result['pattern'] = 'bullish_words_hesitant_body'
                result['reasoning'] = f"Bullish text (sentiment={text_sentiment:.2f}) conflicts with video (conflict={text_video_conflict:.2f})"
                return result
        
        # Check audio-video conflict (nervous voice + hesitant body = uncertainty)
        if audio_embedding is not None and video_embedding is not None:
            av_sim = self._cosine_similarity(audio_embedding, video_embedding)
            av_conflict = 1.0 - _clamp(av_sim)
            
            if av_conflict > self.DECEPTION_THRESHOLD:
                result['deception_detected'] = True
                result['confidence'] = 0.65
                result['pattern'] = 'inconsistent_delivery'
                result['reasoning'] = f"Audio and video show inconsistent delivery (conflict={av_conflict:.2f})"
                return result
        
        result['reasoning'] = "No deception patterns detected"
        return result
