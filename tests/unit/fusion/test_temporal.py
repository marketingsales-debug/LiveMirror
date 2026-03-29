"""
Unit tests for TemporalTransformer and ContextWindowManager.
Owner: Claude
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from src.fusion.types import NarrativeStateVector, ModalityEmbedding
from src.fusion.context.window import ContextWindowManager
from src.fusion.attention.temporal import TemporalTransformer


class TestContextWindowManager:
    """Test context window management."""
    
    def test_add_and_retrieve_states(self):
        """Add and retrieve states."""
        manager = ContextWindowManager(window_size=10)
        
        states = [
            NarrativeStateVector(timestamp=datetime.now(), signal_id=f"sig_{i}", platform="twitter")
            for i in range(5)
        ]
        
        for state in states:
            manager.add_state(state)
        
        assert len(manager.get_recent()) == 5
        assert manager.is_full() is False
    
    def test_window_capacity(self):
        """Window respects size limit."""
        manager = ContextWindowManager(window_size=5)
        
        for i in range(10):
            state = NarrativeStateVector(timestamp=datetime.now(), signal_id=f"sig_{i}")
            manager.add_state(state)
        
        assert len(manager.get_recent()) == 5
        assert manager.is_full() is True
    
    def test_get_by_platform(self):
        """Filter states by platform."""
        manager = ContextWindowManager(window_size=10)
        
        for i in range(5):
            state = NarrativeStateVector(
                timestamp=datetime.now(),
                signal_id=f"sig_{i}",
                platform="twitter" if i < 3 else "reddit"
            )
            manager.add_state(state)
        
        twitter_states = manager.get_by_platform("twitter")
        assert len(twitter_states) == 3


class TestTemporalTransformer:
    """Test temporal dynamics computation."""
    
    def test_positional_encoding_shape(self):
        """Positional encoding has correct shape."""
        transformer = TemporalTransformer(embedding_dim=384, max_seq_len=50)
        
        assert transformer.pos_encoding.shape == (50, 384)
        assert np.all(np.isfinite(transformer.pos_encoding))
    
    def test_compute_temporal_state_short_sequence(self):
        """Returns None for sequences < 2."""
        transformer = TemporalTransformer()
        
        state = NarrativeStateVector(
            timestamp=datetime.now(),
            signal_id="sig_1",
        )
        
        result = transformer.compute_temporal_state([state])
        assert result is None
    
    def test_compute_temporal_state_valid_sequence(self):
        """Compute temporal state from valid sequence."""
        transformer = TemporalTransformer()
        
        states = [
            NarrativeStateVector(
                timestamp=datetime.now() + timedelta(seconds=i),
                signal_id=f"sig_{i}",
                fused_embedding=np.random.randn(384).astype(np.float32)
            )
            for i in range(5)
        ]
        
        result = transformer.compute_temporal_state(states)
        assert result is not None
        assert result.embedding.shape == (384,)
        assert result.velocity.shape == (384,)
        assert result.acceleration.shape == (384,)
        assert isinstance(result.momentum, float)
    
    def test_velocity_computation(self):
        """Velocity is computed correctly."""
        transformer = TemporalTransformer()
        
        # Create simple sequence: constant change
        embeddings = [
            np.ones(384, dtype=np.float32) * i
            for i in range(5)
        ]
        
        vel = transformer._compute_velocity(embeddings)
        assert vel.shape == (384,)
        # Average velocity should be close to 1.0 (constant increase)
        assert np.allclose(vel, 1.0, atol=0.1)
