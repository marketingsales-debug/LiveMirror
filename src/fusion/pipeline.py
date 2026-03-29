"""
Multimodal Fusion Pipeline — orchestrates entire fusion flow.
Owner: Claude

Integrates encoders, attention, temporal, audiences, and noise detection.
"""

import numpy as np
from typing import Optional, Dict, List
from datetime import datetime

from .types import NarrativeStateVector, MultiAudiencePrediction, FusionConfig
from .encoders.text import TextEncoder
from .encoders.audio import AudioEncoder
from .encoders.video import VideoEncoder
from .attention.cross_modal import CrossModalTransformer
from .attention.temporal import TemporalTransformer
from .context.window import ContextWindowManager
from .audiences.heads import MultiAudiencePredictionHead
from .noise import NoiseDetector


class FusionPipeline:
    """Complete multimodal fusion pipeline."""
    
    def __init__(self, config: Optional[FusionConfig] = None):
        """Initialize fusion pipeline."""
        self.config = config or FusionConfig()
        
        # Encoders
        self.text_encoder = TextEncoder()
        self.audio_encoder = AudioEncoder()
        self.video_encoder = VideoEncoder()
        
        # Fusion layers
        self.cross_modal = CrossModalTransformer(
            dim=self.config.embedding_dim,
            num_heads=self.config.num_attention_heads,
            num_layers=self.config.attention_layers,
        )
        self.temporal_transformer = TemporalTransformer()
        self.context_manager = ContextWindowManager(
            window_size=self.config.context_window_size
        )
        
        # Prediction head
        self.prediction_head = MultiAudiencePredictionHead(
            self.config.audience_segments
        )
        
        # Noise detection
        self.noise_detector = NoiseDetector()
    
    def process_signal(
        self,
        content: str,
        audio_source: Optional[str] = None,
        video_source: Optional[str] = None,
        platform: str = "",
        engagement: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[MultiAudiencePrediction]:
        """
        Process a signal through the complete fusion pipeline.
        
        Args:
            content: Text content
            audio_source: Optional audio URL/path
            video_source: Optional video URL/path
            platform: Source platform
            engagement: Engagement metrics
            metadata: Additional metadata
        
        Returns:
            MultiAudiencePrediction or None if error
        """
        try:
            # 1. Encode modalities
            embeddings = {}
            
            if self.config.enable_text:
                text_emb = self.text_encoder.encode(content)
                if text_emb:
                    embeddings["text"] = text_emb.embedding
            
            if self.config.enable_audio and audio_source:
                audio_emb = self.audio_encoder.encode(audio_source)
                if audio_emb:
                    embeddings["audio"] = audio_emb.embedding
            
            if self.config.enable_video and video_source:
                video_emb = self.video_encoder.encode(video_source, metadata=metadata)
                if video_emb:
                    embeddings["video"] = video_emb.embedding
            
            if not embeddings:
                return None
            
            # 2. Cross-modal fusion
            fused_embedding = self.cross_modal.fuse(embeddings)
            
            # 3. Create narrative state
            state = NarrativeStateVector(
                timestamp=datetime.now(),
                signal_id=metadata.get("signal_id", "") if metadata else "",
                fused_embedding=fused_embedding,
                platform=platform,
                engagement_score=engagement.get("likes", 0) if engagement else 0.0,
                url=metadata.get("url") if metadata else None,
            )
            
            # Add to context
            self.context_manager.add_state(state)
            
            # 4. Compute temporal dynamics
            recent_states = self.context_manager.get_recent(num_states=10)
            temporal_state = self.temporal_transformer.compute_temporal_state(recent_states)
            
            if temporal_state is None:
                # First prediction, create default temporal state
                temporal_state = self.temporal_transformer.compute_temporal_state(
                    recent_states + [state]
                ) or self._create_default_temporal_state(fused_embedding)
            
            # 5. Platform signal extraction (simplified)
            platform_signals = {
                platform: float(np.tanh(np.linalg.norm(fused_embedding) / 100.0))
                if platform else 0.0
            }
            
            # 6. Multi-audience prediction
            prediction = self.prediction_head.predict(
                fused_embedding,
                temporal_state,
                platform_signals,
            )
            
            # 7. Noise adjustment
            if self.config.use_sarcasm_detection or self.config.use_spam_scoring:
                adjusted_conf = self.noise_detector.adjust_confidence(
                    prediction.consensus_confidence,
                    content,
                    engagement or {},
                )
                prediction.consensus_confidence = adjusted_conf
            
            return prediction
        except Exception:
            return None
    
    def _create_default_temporal_state(self, embedding: np.ndarray):
        """Create default temporal state for first signal."""
        from .types import TemporalState
        
        return TemporalState(
            timestamp=datetime.now(),
            embedding=embedding,
            velocity=np.zeros_like(embedding),
            acceleration=np.zeros_like(embedding),
            momentum=0.0,
        )
