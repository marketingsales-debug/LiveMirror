"""
Text Encoder — wraps SemanticScorer for 384-dimensional embeddings.
Owner: Claude
"""

import numpy as np
from typing import Optional
from datetime import datetime

from ..types import ModalityEmbedding
from ...ingestion.embeddings import SemanticScorer


class TextEncoder:
    """Encode text content to 384-dimensional embeddings."""
    
    def __init__(self):
        """Initialize with SemanticScorer."""
        self.scorer = SemanticScorer()
        self._embedding_model = None
        self._try_load_embedding_model()
    
    def _try_load_embedding_model(self) -> None:
        """Try to load the underlying embedding model for direct access."""
        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            pass
    
    def available(self) -> bool:
        """Text encoding always available (fallback to TF-IDF)."""
        return True
    
    def encode(self, text: str, timestamp: Optional[datetime] = None) -> ModalityEmbedding:
        """
        Encode text to 384-dimensional embedding.
        
        Args:
            text: Input text content
            timestamp: Optional timestamp for the embedding
        
        Returns:
            ModalityEmbedding with 384-dim vector
        """
        if not text or not text.strip():
            return ModalityEmbedding(
                modality="text",
                embedding=np.zeros(384, dtype=np.float32),
                confidence=0.0,
                timestamp=timestamp or datetime.now(),
            )
        
        # Use sentence-transformer if available, else use TF-IDF fallback
        if self._embedding_model:
            embedding = self._embedding_model.encode(text)
            # Normalize to unit length
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
        else:
            # Fallback: TF-IDF-based embedding (simplified)
            embedding = self._tfidf_embedding(text)
        
        # Ensure 384-dim
        embedding = embedding.astype(np.float32)
        if len(embedding) != 384:
            # Pad or truncate (shouldn't happen with sentence-transformers)
            if len(embedding) < 384:
                embedding = np.pad(embedding, (0, 384 - len(embedding)))
            else:
                embedding = embedding[:384]
        
        return ModalityEmbedding(
            modality="text",
            embedding=embedding,
            confidence=0.9,  # High confidence for text
            timestamp=timestamp or datetime.now(),
        )
    
    def _tfidf_embedding(self, text: str) -> np.ndarray:
        """
        Create a simple TF-IDF embedding (384-dim).
        
        This is a fallback when sentence-transformers is unavailable.
        Uses character n-grams hashed to 384 dimensions.
        """
        from collections import Counter
        import hashlib
        
        # Extract character bigrams
        bigrams = [text[i:i+2] for i in range(len(text)-1)]
        bigram_counts = Counter(bigrams)
        
        # Hash bigrams to 384 bins
        embedding = np.zeros(384, dtype=np.float32)
        for bigram, count in bigram_counts.items():
            hash_val = int(hashlib.md5(bigram.encode()).hexdigest(), 16)
            idx = hash_val % 384
            embedding[idx] += count
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
