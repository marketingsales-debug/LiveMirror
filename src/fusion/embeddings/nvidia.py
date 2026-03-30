"""
NVIDIA Embeddings Integration.
Replaces local SentenceTransformers with high-performance NIM embeddings.
"""

from typing import List
from ...shared.llm import LLMFactory

class NVIDIAEmbedder:
    """Wrapper for NVIDIA Embeddings NIM."""

    def __init__(self):
        self.client = LLMFactory.get_embeddings()

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query."""
        return self.client.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of documents."""
        return self.client.embed_documents(texts)
