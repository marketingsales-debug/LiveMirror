"""
Unit tests for LearnedCrossModalAttention.
Owner: Claude
"""

import pytest
import torch
import numpy as np
from src.fusion.attention.learned_cross_modal import LearnedCrossModalAttention

class TestLearnedAttention:
    """Test LearnedCrossModalAttention logic and gradient flow."""
    
    def test_forward_pass_dims(self):
        """Verify forward pass output shape."""
        model = LearnedCrossModalAttention(embedding_dim=384, num_layers=3)
        embeddings = {
            "text": np.random.rand(384).astype(np.float32),
            "audio": np.random.rand(384).astype(np.float32),
            "video": np.random.rand(384).astype(np.float32)
        }
        
        output = model.forward(embeddings)
        assert output.shape == (384,)
        assert output.dtype == np.float32
        
    def test_gradient_flow_fine_tune(self):
        """Verify weights update after fine-tuning loop."""
        torch.manual_seed(42)
        model = LearnedCrossModalAttention(embedding_dim=384, num_layers=2)
        
        # Capture initial weights
        init_weights = model.output_projection.weight.detach().clone()
        
        input_dict = {"text": np.random.rand(384).astype(np.float32)}
        target = np.random.rand(384).astype(np.float32)
        
        # Fine-tune
        model.fine_tune_on_data([input_dict], [target])
        
        # Compare weights
        final_weights = model.output_projection.weight.detach()
        assert not torch.equal(init_weights, final_weights)
        
    def test_handle_empty_input(self):
        """Verify model handles empty modality dict gracefully."""
        model = LearnedCrossModalAttention(embedding_dim=384)
        output = model.forward({})
        assert np.array_equal(output, np.zeros(384))
        
    def test_single_modality_pass(self):
        """Verify model functions correctly with only one modality."""
        model = LearnedCrossModalAttention(embedding_dim=384)
        text_emb = np.random.rand(384).astype(np.float32)
        output = model.forward({"text": text_emb})
        assert output.shape == (384,)
        # Should not be equal due to learned projections/layers
        assert not np.array_equal(output, text_emb)
