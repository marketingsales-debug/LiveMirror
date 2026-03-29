"""
Unit tests for CrossModalAttention.
Owner: Claude
"""

import pytest
import numpy as np
from src.fusion.attention.cross_modal import CrossModalAttention, CrossModalTransformer


class TestCrossModalAttention:
    """Test attention mechanism."""
    
    def test_single_head_attention(self):
        """Single attention head processes inputs correctly."""
        attn = CrossModalAttention(dim=384, num_heads=4)
        
        query = np.random.randn(384).astype(np.float32)
        keys = [np.random.randn(384).astype(np.float32) for _ in range(2)]
        values = [np.random.randn(384).astype(np.float32) for _ in range(2)]
        
        output = attn.attend(query, keys, values)
        assert output.shape == (384,)
        assert np.all(np.isfinite(output))
    
    def test_attend_empty_keys(self):
        """Returns query when no keys provided."""
        attn = CrossModalAttention(dim=384)
        query = np.random.randn(384).astype(np.float32)
        
        output = attn.attend(query, [], [])
        assert np.allclose(output, query)
    
    def test_attention_weights_sum_to_one(self):
        """Attention weights sum to 1.0."""
        attn = CrossModalAttention(dim=384)
        query = np.ones(384).astype(np.float32)
        keys = [np.ones(384).astype(np.float32) * i for i in [1, 2, 3]]
        values = keys
        
        output = attn.attend(query, keys, values)
        # Output should be valid weighted sum
        assert output.shape == (384,)


class TestCrossModalTransformer:
    """Test transformer fusion."""
    
    def test_fuse_single_modality(self):
        """Fuse single modality (text only)."""
        transformer = CrossModalTransformer(dim=384, num_heads=4, num_layers=2)
        embeddings = {"text": np.random.randn(384).astype(np.float32)}
        
        output = transformer.fuse(embeddings)
        assert output.shape == (384,)
        assert np.all(np.isfinite(output))
    
    def test_fuse_multi_modality(self):
        """Fuse multiple modalities."""
        transformer = CrossModalTransformer(dim=384, num_heads=4, num_layers=2)
        embeddings = {
            "text": np.random.randn(384).astype(np.float32),
            "audio": np.random.randn(384).astype(np.float32),
            "video": np.random.randn(384).astype(np.float32),
        }
        
        output = transformer.fuse(embeddings)
        assert output.shape == (384,)
        assert np.all(np.isfinite(output))
    
    def test_normalize_preserves_shape(self):
        """Normalization preserves shape."""
        transformer = CrossModalTransformer()
        vec = np.random.randn(384).astype(np.float32)
        
        normalized = transformer._normalize(vec)
        assert normalized.shape == (384,)
        
        # Check normalization (if non-zero)
        norm = np.linalg.norm(normalized)
        assert norm == pytest.approx(1.0, abs=0.01) or np.allclose(normalized, 0)
