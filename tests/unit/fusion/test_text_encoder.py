"""
Unit tests for TextEncoder.
Owner: Claude
"""

import pytest
import numpy as np
from datetime import datetime
from src.fusion.encoders.text import TextEncoder


class TestTextEncoder:
    """Test TextEncoder functionality."""
    
    def test_encoder_available(self):
        """Text encoder is always available."""
        encoder = TextEncoder()
        assert encoder.available() is True
    
    def test_encode_valid_text(self):
        """Encode valid text produces 384-dim embedding."""
        encoder = TextEncoder()
        embedding = encoder.encode("Bitcoin is rallying")
        
        assert embedding.modality == "text"
        assert embedding.embedding.shape == (384,)
        assert embedding.confidence >= 0.8
        assert isinstance(embedding.timestamp, datetime)
    
    def test_encode_empty_text(self):
        """Empty text produces zero embedding."""
        encoder = TextEncoder()
        embedding = encoder.encode("")
        
        assert embedding.embedding.shape == (384,)
        assert np.allclose(embedding.embedding, 0.0)
        assert embedding.confidence == 0.0
    
    def test_encode_whitespace_only(self):
        """Whitespace-only text produces zero embedding."""
        encoder = TextEncoder()
        embedding = encoder.encode("   \n\t  ")
        
        assert embedding.embedding.shape == (384,)
        assert np.allclose(embedding.embedding, 0.0)
        assert embedding.confidence == 0.0
    
    def test_embedding_is_normalized(self):
        """Embeddings are normalized (unit length or close)."""
        encoder = TextEncoder()
        embedding = encoder.encode("Some text")
        
        norm = np.linalg.norm(embedding.embedding)
        # Should be close to 1.0 if normalized, or 0 if empty
        assert norm == pytest.approx(1.0, abs=0.1) or norm == pytest.approx(0.0, abs=0.1)
    
    def test_same_text_same_embedding(self):
        """Same text produces same embedding."""
        encoder = TextEncoder()
        text = "Consistent text"
        emb1 = encoder.encode(text).embedding
        emb2 = encoder.encode(text).embedding
        
        assert np.allclose(emb1, emb2)
    
    def test_different_text_different_embedding(self):
        """Different texts produce different embeddings."""
        encoder = TextEncoder()
        emb1 = encoder.encode("Bitcoin").embedding
        emb2 = encoder.encode("Ethereum").embedding
        
        # Should be different (not all close)
        assert not np.allclose(emb1, emb2)
    
    def test_encode_with_timestamp(self):
        """Can provide custom timestamp."""
        encoder = TextEncoder()
        ts = datetime(2025, 1, 1, 12, 0, 0)
        embedding = encoder.encode("Text", timestamp=ts)
        
        assert embedding.timestamp == ts
