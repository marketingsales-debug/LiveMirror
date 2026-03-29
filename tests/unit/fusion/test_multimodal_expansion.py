"""
Unit tests for 4-modality fusion expansion.
Owner: Claude
"""

import pytest
import numpy as np
from src.fusion.attention.learned_cross_modal import LearnedCrossModalAttention

class TestMultimodalExpansion:
    """Test that the transformer handles the addition of the 4th modality."""
    
    def test_fuse_4_modalities(self):
        """Verify 4 modalities (Text, Audio, Video, Sentiment) are fused correctly."""
        model = LearnedCrossModalAttention(embedding_dim=384)
        
        embeddings = {
            "text": np.random.rand(384).astype(np.float32),
            "audio": np.random.rand(384).astype(np.float32),
            "video": np.random.rand(384).astype(np.float32),
            "sentiment": np.random.rand(384).astype(np.float32)
        }
        
        output = model.forward(embeddings)
        assert output.shape == (384,)
        assert output.dtype == np.float32
        
    def test_modality_agnostic_fusion(self):
        """Verify the transformer doesn't care about modality names/counts."""
        model = LearnedCrossModalAttention(embedding_dim=384)
        
        e1 = {"text": np.ones(384)}
        e2 = {"text": np.ones(384), "audio": np.ones(384), "video": np.ones(384), "sentiment": np.ones(384)}
        
        o1 = model.forward(e1)
        o2 = model.forward(e2)
        
        assert o1.shape == (384,)
        assert o2.shape == (384,)
        # Should be different as the transformer attends to all provided keys
        assert not np.array_equal(o1, o2)
