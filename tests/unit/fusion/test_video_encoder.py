"""
Unit tests for VideoEncoder (synthetic tensors).
Owner: Claude
"""

import pytest
import numpy as np
from datetime import datetime
from src.fusion.encoders.video import VideoEncoder


class TestVideoEncoder:
    """Test VideoEncoder functionality."""
    
    def test_encoder_graceful_init(self):
        """Video encoder initializes even without CLIP."""
        encoder = VideoEncoder()
        assert isinstance(encoder.available(), bool)
    
    def test_none_on_unavailable(self):
        """Returns None if encoder unavailable."""
        encoder = VideoEncoder()
        encoder._use_clip = False
        
        result = encoder.encode("/fake/video.mp4")
        assert result is None
    
    def test_project_to_384_pad(self):
        """Projection pads short embeddings."""
        encoder = VideoEncoder()
        short_emb = np.random.randn(256).astype(np.float32)
        
        result = encoder._project_to_384(short_emb)
        assert result.shape == (384,)
        assert np.allclose(result[:256], short_emb)
        assert np.allclose(result[256:], 0.0)
    
    def test_project_to_384_truncate(self):
        """Projection truncates long embeddings."""
        encoder = VideoEncoder()
        long_emb = np.random.randn(512).astype(np.float32)
        
        result = encoder._project_to_384(long_emb)
        assert result.shape == (384,)
        assert np.allclose(result, long_emb[:384])
    
    def test_project_to_384_exact(self):
        """Projection preserves exact 384-dim embeddings."""
        encoder = VideoEncoder()
        emb_384 = np.random.randn(384).astype(np.float32)
        
        result = encoder._project_to_384(emb_384)
        assert result.shape == (384,)
        assert np.allclose(result, emb_384)
