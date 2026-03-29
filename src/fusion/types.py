"""
Fusion Layer Type Definitions
Owner: Claude

Core data structures for multimodal fusion, temporal modeling,
and multi-audience prediction.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from datetime import datetime
import numpy as np


@dataclass
class ModalityEmbedding:
    """Single modality embedding (384-dimensional)."""
    modality: Literal["text", "audio", "video"]
    embedding: np.ndarray  # shape (384,)
    confidence: float = 1.0  # Encoder confidence
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate embedding dimensions."""
        if self.embedding.shape != (384,):
            raise ValueError(f"Expected shape (384,), got {self.embedding.shape}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass
class NarrativeStateVector:
    """Combined multimodal state at a single timestamp."""
    timestamp: datetime
    signal_id: str
    
    # Modality embeddings
    text_embedding: Optional[ModalityEmbedding] = None
    audio_embedding: Optional[ModalityEmbedding] = None
    video_embedding: Optional[ModalityEmbedding] = None
    
    # Fused cross-modal representation
    fused_embedding: Optional[np.ndarray] = None  # shape (384,)
    
    # Metadata
    platform: str = ""
    engagement_score: float = 0.0
    url: Optional[str] = None
    
    def available_modalities(self) -> List[str]:
        """Return list of available modalities."""
        mods = []
        if self.text_embedding is not None:
            mods.append("text")
        if self.audio_embedding is not None:
            mods.append("audio")
        if self.video_embedding is not None:
            mods.append("video")
        return mods
    
    def get_available_embeddings(self) -> List[np.ndarray]:
        """Get all available embeddings."""
        embs = []
        if self.text_embedding is not None:
            embs.append(self.text_embedding.embedding)
        if self.audio_embedding is not None:
            embs.append(self.audio_embedding.embedding)
        if self.video_embedding is not None:
            embs.append(self.video_embedding.embedding)
        return embs


@dataclass
class TemporalState:
    """Temporal dynamics: velocity, acceleration, momentum."""
    timestamp: datetime
    embedding: np.ndarray  # shape (384,)
    
    # Temporal derivatives
    velocity: np.ndarray  # shape (384,) — first derivative
    acceleration: np.ndarray  # shape (384,) — second derivative
    momentum: float = 0.0  # Trend strength
    
    def __post_init__(self):
        """Validate dimensions."""
        if self.embedding.shape != (384,):
            raise ValueError(f"Embedding shape mismatch: {self.embedding.shape}")
        if self.velocity.shape != (384,):
            raise ValueError(f"Velocity shape mismatch: {self.velocity.shape}")
        if self.acceleration.shape != (384,):
            raise ValueError(f"Acceleration shape mismatch: {self.acceleration.shape}")


@dataclass
class AudienceSegment:
    """Audience segment configuration."""
    name: str
    platform_weights: Dict[str, float]  # e.g., {"twitter": 0.8, "reddit": 0.2}
    modality_weights: Dict[str, float] = field(
        default_factory=lambda: {"text": 0.5, "audio": 0.3, "video": 0.2}
    )
    
    def __post_init__(self):
        """Validate weights sum to ~1.0."""
        total_plat = sum(self.platform_weights.values())
        total_mod = sum(self.modality_weights.values())
        if not (0.95 <= total_plat <= 1.05):
            raise ValueError(f"Platform weights must sum to 1.0, got {total_plat}")
        if not (0.95 <= total_mod <= 1.05):
            raise ValueError(f"Modality weights must sum to 1.0, got {total_mod}")


@dataclass
class SegmentPrediction:
    """Prediction for a single audience segment."""
    segment_name: str
    direction: float  # -1.0 (down) to +1.0 (up)
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""
    modality_contributions: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate ranges."""
        if not -1.0 <= self.direction <= 1.0:
            raise ValueError(f"Direction must be in [-1, 1], got {self.direction}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass
class MultiAudiencePrediction:
    """Multi-audience consensus prediction."""
    timestamp: datetime
    segment_predictions: List[SegmentPrediction] = field(default_factory=list)
    
    # Aggregate metrics
    consensus_direction: float = 0.0  # Mean direction across segments
    consensus_confidence: float = 0.0  # Mean confidence
    cross_segment_agreement: float = 0.0  # 0-1, how aligned are segments?
    
    def add_segment_prediction(self, pred: SegmentPrediction) -> None:
        """Add a segment prediction and recompute consensus."""
        self.segment_predictions.append(pred)
        self._compute_consensus()
    
    def _compute_consensus(self) -> None:
        """Recompute consensus metrics."""
        if not self.segment_predictions:
            self.consensus_direction = 0.0
            self.consensus_confidence = 0.0
            self.cross_segment_agreement = 0.0
            return
        
        directions = [p.direction for p in self.segment_predictions]
        confidences = [p.confidence for p in self.segment_predictions]
        
        self.consensus_direction = sum(directions) / len(directions)
        self.consensus_confidence = sum(confidences) / len(confidences)
        
        # Agreement: how close directions are (using std dev)
        if len(directions) > 1:
            direction_std = float(np.std(directions))
            self.cross_segment_agreement = 1.0 - min(1.0, direction_std)
        else:
            self.cross_segment_agreement = 1.0


@dataclass
class FusionConfig:
    """Configuration for multimodal fusion pipeline."""
    embedding_dim: int = 384
    
    # Encoder availability flags
    enable_text: bool = True
    enable_audio: bool = True
    enable_video: bool = True
    
    # Cross-modal attention
    num_attention_heads: int = 4
    attention_layers: int = 2
    attention_hidden_dim: int = 512
    
    # Temporal modeling
    context_window_size: int = 50  # Number of previous states to track
    temporal_dropout: float = 0.1
    
    # Audience segments
    audience_segments: List[AudienceSegment] = field(default_factory=list)
    
    # Feature flags
    use_sarcasm_detection: bool = True
    use_spam_scoring: bool = True
    
    def __post_init__(self):
        """Set default audience segments if not provided."""
        if not self.audience_segments:
            self.audience_segments = [
                AudienceSegment(
                    name="crypto_twitter",
                    platform_weights={"twitter": 0.8, "bluesky": 0.15, "reddit": 0.05},
                ),
                AudienceSegment(
                    name="mainstream_media",
                    platform_weights={"news": 0.7, "web": 0.2, "hackernews": 0.1},
                ),
                AudienceSegment(
                    name="retail_investors",
                    platform_weights={"twitter": 0.6, "reddit": 0.3, "web": 0.1},
                ),
                AudienceSegment(
                    name="tech_community",
                    platform_weights={"hackernews": 0.6, "twitter": 0.3, "bluesky": 0.1},
                ),
            ]
