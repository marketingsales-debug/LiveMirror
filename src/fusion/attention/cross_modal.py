"""
Cross-Modal Attention Transformer
Owner: Claude

2-layer Transformer with multi-head cross-attention (4 heads, 384-dim).
Fuses text, audio, video embeddings into unified representation.
"""

import numpy as np
from typing import List, Optional
from datetime import datetime


class CrossModalAttention:
    """Single cross-modal attention head."""
    
    def __init__(self, dim: int = 384, num_heads: int = 4):
        """Initialize attention parameters."""
        self.dim = dim
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        
        # Query, Key, Value projections (simplified, no learned params)
        self.scale = 1.0 / np.sqrt(self.head_dim)
    
    def attend(self, query: np.ndarray, keys: List[np.ndarray], values: List[np.ndarray]) -> np.ndarray:
        """
        Multi-head cross-modal attention.
        
        Args:
            query: Primary embedding (384,)
            keys: List of key embeddings from different modalities
            values: List of value embeddings from different modalities
        
        Returns:
            Attended output (384,)
        """
        if not keys or not values:
            return query
        
        # Stack keys and values
        keys_stacked = np.stack(keys, axis=0)  # (num_modalities, 384)
        values_stacked = np.stack(values, axis=0)  # (num_modalities, 384)
        
        # Compute attention scores (simplified dot-product)
        scores = np.dot(query, keys_stacked.T)  # (num_modalities,)
        
        # Softmax
        exp_scores = np.exp(scores - np.max(scores))
        attn_weights = exp_scores / (np.sum(exp_scores) + 1e-8)
        
        # Apply attention to values
        output = np.sum(values_stacked * attn_weights[:, None], axis=0)
        
        return output.astype(np.float32)


class CrossModalTransformer:
    """2-layer Transformer with cross-modal attention."""
    
    def __init__(self, dim: int = 384, num_heads: int = 4, num_layers: int = 2):
        """Initialize transformer."""
        self.dim = dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.heads = [CrossModalAttention(dim, num_heads) for _ in range(num_layers)]
    
    def fuse(self, embeddings: dict) -> np.ndarray:
        """
        Fuse multimodal embeddings through cross-modal attention.
        
        Args:
            embeddings: Dict with keys: 'text', 'audio', 'video' (optional)
            Example: {"text": array(384,), "audio": array(384,)}
        
        Returns:
            Fused 384-dimensional embedding
        """
        # Start with text embedding (primary modality)
        output = embeddings.get("text", np.zeros(384, dtype=np.float32))
        
        # Get available embeddings
        available_keys = [k for k in embeddings.keys() if k != "text"]
        if not available_keys:
            return output
        
        # Apply attention layers
        for layer in self.heads:
            keys = [embeddings[k] for k in available_keys]
            values = [embeddings[k] for k in available_keys]
            output = layer.attend(output, keys, values)
            output = self._normalize(output)
        
        return output.astype(np.float32)
    
    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Normalize vector to unit length."""
        norm = np.linalg.norm(vec)
        if norm > 0:
            return vec / norm
        return vec
