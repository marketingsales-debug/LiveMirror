"""
Multimodal Fusion Pipeline — orchestrates entire fusion flow.
Owner: Claude

Integrates encoders, attention, temporal, audiences, and noise detection.
"""

import logging
import numpy as np
from typing import Optional, Dict, List, Any
from datetime import datetime

from .types import NarrativeStateVector, MultiAudiencePrediction, FusionConfig
from .encoders.text import TextEncoder
from .encoders.audio import AudioEncoder
from .encoders.video import VideoEncoder
from .encoders.sentiment import SentimentEncoder
from .analysis.intent import IntentDetector
from .reasoning import CrossModalReasoning
from .attention.cross_modal import CrossModalTransformer
from .attention.learned_cross_modal import LearnedCrossModalAttention
from .attention.temporal import TemporalTransformer
from .context.window import ContextWindowManager
from .audiences.heads import MultiAudiencePredictionHead
from .noise import NoiseDetector
from .cache.embedding_cache import EmbeddingCache


class FusionPipeline:
    """Complete multimodal fusion pipeline."""

    logger = logging.getLogger(__name__)
    
    def __init__(self, config: Optional[FusionConfig] = None):
        """Initialize fusion pipeline."""
        self.config = config or FusionConfig()
        
        # Encoders
        self.text_encoder = TextEncoder()
        self.audio_encoder = AudioEncoder()
        self.video_encoder = VideoEncoder()
        self.sentiment_encoder = SentimentEncoder()
        
        # Advanced Analysis layers
        self.intent_detector = IntentDetector()
        self.reasoning_engine = CrossModalReasoning()
        
        # Fusion layers
        self.cross_modal_fixed = CrossModalTransformer(
            dim=self.config.embedding_dim,
            num_heads=self.config.num_attention_heads,
            num_layers=self.config.attention_layers,
        )
        self.cross_modal_learned = LearnedCrossModalAttention(
            embedding_dim=self.config.embedding_dim,
            num_heads=8,  # Roadmap: 8 heads
            num_layers=3, # Roadmap: 3 layers
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
        
        # Cache (Efficiency Foundation)
        self.cache = EmbeddingCache(max_size=self.config.embedding_cache_size)
    
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
            metadata = metadata or {}
            engagement = engagement or {}

            # 1. Encode modalities
            embeddings = {}
            
            if self.config.enable_text:
                # Check cache first (7x latency reduction)
                cached_text = self.cache.get(content, "text")
                if cached_text is not None:
                    embeddings["text"] = cached_text
                else:
                    text_emb = self.text_encoder.encode(content)
                    if text_emb:
                        embeddings["text"] = text_emb.embedding
                        self.cache.set(content, text_emb.embedding, "text")
            
            if self.config.enable_audio and audio_source:
                cached_audio = self.cache.get(audio_source, "audio")
                if cached_audio is not None:
                    embeddings["audio"] = cached_audio
                else:
                    audio_emb = self.audio_encoder.encode(audio_source)
                    if audio_emb:
                        embeddings["audio"] = audio_emb.embedding
                        self.cache.set(audio_source, audio_emb.embedding, "audio")
            
            if self.config.enable_video and video_source:
                cached_video = self.cache.get(video_source, "video")
                if cached_video is not None:
                    embeddings["video"] = cached_video
                else:
                    video_emb = self.video_encoder.encode(video_source, metadata=metadata)
                    if video_emb:
                        embeddings["video"] = video_emb.embedding
                        self.cache.set(video_source, video_emb.embedding, "video")
            
            if self.config.enable_sentiment:
                cached_sentiment = self.cache.get(content, "sentiment")
                if cached_sentiment is not None:
                    embeddings["sentiment"] = cached_sentiment
                else:
                    sentiment_res = self.sentiment_encoder.encode(content)
                    if sentiment_res:
                        embeddings["sentiment"] = sentiment_res["embedding"]
                        self.cache.set(content, sentiment_res["embedding"], "sentiment")
            
            if not embeddings:
                return None
            
            # 2. Cross-modal fusion
            if self.config.use_learned_attention:
                fused_embedding = self.cross_modal_learned(embeddings)
            else:
                fused_embedding = self.cross_modal_fixed.fuse(embeddings)

            fused_embedding = self._sanitize_embedding(fused_embedding)
            if fused_embedding is None:
                self.logger.warning("Fused embedding invalid; skipping signal.")
                return None
            
            # 2b. Compute Modality Alignment (Reasoning Phase)
            alignment_report = self.reasoning_engine.compute_modality_alignment(embeddings)
            
            # 3. Create narrative state
            state = NarrativeStateVector(
                timestamp=datetime.now(),
                signal_id=metadata.get("signal_id", ""),
                fused_embedding=fused_embedding,
                platform=platform,
                engagement_score=engagement.get("likes", 0),
                url=metadata.get("url"),
            )
            
            # Map modality-specific embeddings for state persistence
            if "text" in embeddings:
                from .types import ModalityEmbedding
                state.text_embedding = ModalityEmbedding("text", embeddings["text"])
            if "audio" in embeddings:
                from .types import ModalityEmbedding
                state.audio_embedding = ModalityEmbedding("audio", embeddings["audio"])
            if "video" in embeddings:
                from .types import ModalityEmbedding
                state.video_embedding = ModalityEmbedding("video", embeddings["video"])
            if "sentiment" in embeddings:
                from .types import ModalityEmbedding
                state.sentiment_embedding = ModalityEmbedding("sentiment", embeddings["sentiment"])
            
            # 3b. Intent and Credibility Detection
            intent_res = self.intent_detector.determine_intent(
                content, metadata.get("author", {})
            )
            state.intent = intent_res["intent"]
            state.credibility_score = intent_res["credibility"]
            state.manipulation_risk = alignment_report["conflict"]
            
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
            
            # 4. Audience prediction
            prediction = self.prediction_head.predict(
                fused_embedding,
                temporal_state,
                platform_signals
            )
            
            # 4b. Apply Reasoning Penalty/Boost
            prediction = self.reasoning_engine.final_prediction_with_reasoning(
                prediction, alignment_report
            )
            
            # Post-process with noise detection
            if self.config.use_spam_scoring:
                adjusted_conf = self.noise_detector.adjust_confidence(
                    prediction.consensus_confidence, content, engagement or {}
                )
                prediction.consensus_confidence = adjusted_conf
            
            return prediction
        except Exception:
            self.logger.exception("Fusion pipeline processing failed")
            return None
    
    def fine_tune_attention(self, history: List[Dict[str, Any]], outcomes: List[np.ndarray]):
        """
        Fine-tune the learned attention weights using historical results.
        
        Args:
            history: List of signal dicts (content, audio, video)
            outcomes: List of target embeddings (384,)
        """
        self.cross_modal_learned.fine_tune_on_data(history, outcomes)
            
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

    def _sanitize_embedding(self, embedding: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Validate fused embeddings for downstream safety."""
        if embedding is None:
            return None
        arr = np.asarray(embedding, dtype=np.float32)
        if arr.shape != (self.config.embedding_dim,) or arr.size == 0:
            return None
        if not np.all(np.isfinite(arr)):
            return None
        return arr
