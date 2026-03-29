"""
Unit tests for LRU EmbeddingCache.
Owner: Claude
"""

import pytest
import numpy as np
from src.fusion.cache.embedding_cache import EmbeddingCache

class TestEmbeddingCache:
    """Test EmbeddingCache logic and LRU policy."""
    
    def test_cache_hit_and_miss(self):
        """Test basic get/set functionality."""
        cache = EmbeddingCache(max_size=10)
        content = "Bitcoin reaches new ATH"
        embedding = np.random.rand(384)
        
        # Miss initially
        assert cache.get(content) is None
        assert cache.hits == 0
        assert cache.misses == 1
        
        # Set and Hit
        cache.set(content, embedding)
        retrieved = cache.get(content)
        assert np.array_equal(embedding, retrieved)
        assert cache.hits == 1
        assert cache.misses == 1
        
    def test_lru_eviction(self):
        """Test oldest entries are evicted when full."""
        cache = EmbeddingCache(max_size=2)
        
        e1 = np.random.rand(384)
        e2 = np.random.rand(384)
        e3 = np.random.rand(384)
        
        cache.set("item1", e1)
        cache.set("item2", e2)
        
        # Access item1 to make it most recent
        cache.get("item1")
        
        # Add item3, should evict item2 (least recent)
        cache.set("item3", e3)
        
        assert cache.get("item1") is not None
        assert cache.get("item3") is not None
        assert cache.get("item2") is None
        
    def test_stats(self):
        """Test cache statistics reporting."""
        cache = EmbeddingCache(max_size=100)
        cache.set("hello", np.zeros(384))
        cache.get("hello")  # hit
        cache.get("world")  # miss
        
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 1
