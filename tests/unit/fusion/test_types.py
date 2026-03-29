"""
Unit tests for fusion type definitions.
Owner: Claude
"""

import pytest
import numpy as np
from datetime import datetime
from src.fusion.types import (
    ModalityEmbedding,
    NarrativeStateVector,
    TemporalState,
    AudienceSegment,
    SegmentPrediction,
    MultiAudiencePrediction,
    FusionConfig,
)


class TestModalityEmbedding:
    """Test ModalityEmbedding validation and properties."""
    
    def test_valid_embedding(self):
        """Valid 384-dim embedding."""
        emb = np.random.randn(384).astype(np.float32)
        me = ModalityEmbedding(modality="text", embedding=emb)
        assert me.modality == "text"
        assert me.embedding.shape == (384,)
        assert me.confidence == 1.0
    
    def test_invalid_dimension(self):
        """Invalid embedding dimension raises error."""
        emb = np.random.randn(300).astype(np.float32)
        with pytest.raises(ValueError, match="Expected shape"):
            ModalityEmbedding(modality="text", embedding=emb)
    
    def test_invalid_confidence(self):
        """Invalid confidence raises error."""
        emb = np.random.randn(384).astype(np.float32)
        with pytest.raises(ValueError, match="Confidence must be"):
            ModalityEmbedding(modality="text", embedding=emb, confidence=1.5)


class TestNarrativeStateVector:
    """Test NarrativeStateVector properties."""
    
    def test_single_modality(self):
        """State with single modality."""
        emb = np.random.randn(384).astype(np.float32)
        text_emb = ModalityEmbedding(modality="text", embedding=emb)
        state = NarrativeStateVector(
            timestamp=datetime.now(),
            signal_id="sig_1",
            text_embedding=text_emb,
        )
        assert state.available_modalities() == ["text"]
        assert len(state.get_available_embeddings()) == 1
    
    def test_multi_modality(self):
        """State with multiple modalities."""
        emb = np.random.randn(384).astype(np.float32)
        text_emb = ModalityEmbedding(modality="text", embedding=emb)
        audio_emb = ModalityEmbedding(modality="audio", embedding=emb.copy())
        state = NarrativeStateVector(
            timestamp=datetime.now(),
            signal_id="sig_1",
            text_embedding=text_emb,
            audio_embedding=audio_emb,
        )
        assert set(state.available_modalities()) == {"text", "audio"}
        assert len(state.get_available_embeddings()) == 2


class TestTemporalState:
    """Test TemporalState validation."""
    
    def test_valid_temporal_state(self):
        """Valid temporal state."""
        emb = np.random.randn(384).astype(np.float32)
        vel = np.random.randn(384).astype(np.float32)
        acc = np.random.randn(384).astype(np.float32)
        state = TemporalState(
            timestamp=datetime.now(),
            embedding=emb,
            velocity=vel,
            acceleration=acc,
        )
        assert state.embedding.shape == (384,)
        assert state.velocity.shape == (384,)
        assert state.acceleration.shape == (384,)
    
    def test_invalid_embedding_dim(self):
        """Invalid embedding dimension raises error."""
        vel = np.random.randn(384).astype(np.float32)
        acc = np.random.randn(384).astype(np.float32)
        with pytest.raises(ValueError, match="Embedding shape mismatch"):
            TemporalState(
                timestamp=datetime.now(),
                embedding=np.random.randn(300),
                velocity=vel,
                acceleration=acc,
            )


class TestAudienceSegment:
    """Test AudienceSegment validation."""
    
    def test_valid_segment(self):
        """Valid audience segment."""
        seg = AudienceSegment(
            name="crypto_twitter",
            platform_weights={"twitter": 0.8, "reddit": 0.2},
        )
        assert seg.name == "crypto_twitter"
        assert seg.platform_weights["twitter"] == 0.8
    
    def test_invalid_platform_weights(self):
        """Platform weights must sum to 1.0."""
        with pytest.raises(ValueError, match="Platform weights must sum"):
            AudienceSegment(
                name="bad",
                platform_weights={"twitter": 0.5, "reddit": 0.3},  # Sums to 0.8
            )


class TestSegmentPrediction:
    """Test SegmentPrediction validation."""
    
    def test_valid_prediction(self):
        """Valid segment prediction."""
        pred = SegmentPrediction(
            segment_name="crypto_twitter",
            direction=0.5,
            confidence=0.8,
        )
        assert pred.direction == 0.5
        assert pred.confidence == 0.8
    
    def test_invalid_direction(self):
        """Direction must be in [-1, 1]."""
        with pytest.raises(ValueError, match="Direction must be"):
            SegmentPrediction(
                segment_name="crypto_twitter",
                direction=1.5,
                confidence=0.8,
            )


class TestMultiAudiencePrediction:
    """Test MultiAudiencePrediction consensus."""
    
    def test_consensus_computation(self):
        """Consensus is correctly computed."""
        pred1 = SegmentPrediction(segment_name="seg1", direction=0.5, confidence=0.8)
        pred2 = SegmentPrediction(segment_name="seg2", direction=0.3, confidence=0.7)
        
        multi = MultiAudiencePrediction(timestamp=datetime.now())
        multi.add_segment_prediction(pred1)
        multi.add_segment_prediction(pred2)
        
        assert multi.consensus_direction == pytest.approx(0.4)
        assert multi.consensus_confidence == pytest.approx(0.75)
        assert multi.cross_segment_agreement > 0.0


class TestFusionConfig:
    """Test FusionConfig defaults."""
    
    def test_default_config(self):
        """Default config creates audience segments."""
        config = FusionConfig()
        assert len(config.audience_segments) == 4
        assert config.audience_segments[0].name == "crypto_twitter"
        assert config.embedding_dim == 384
