"""
Semantic Embeddings for signal scoring — replaces keyword overlap.
Owner: Claude

Uses sentence-transformers for local embeddings, or falls back
to a simple TF-IDF approach if the model isn't available.
"""

import math
from typing import List, Dict, Optional
from collections import Counter


class SemanticScorer:
    """
    Computes semantic similarity between query and signal content.

    Strategy:
    1. Try sentence-transformers (best quality, requires model download)
    2. Fall back to TF-IDF cosine similarity (fast, no dependencies)
    """

    def __init__(self):
        self._model = None
        self._use_transformer = False
        self._try_load_transformer()

    def _try_load_transformer(self) -> None:
        """Try to load sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._use_transformer = True
        except ImportError:
            pass

    def similarity(self, query: str, text: str) -> float:
        """
        Compute semantic similarity (0.0–1.0) between query and text.
        """
        if not query or not text:
            return 0.0

        if self._use_transformer and self._model:
            return self._transformer_similarity(query, text)
        return self._tfidf_similarity(query, text)

    def batch_similarity(self, query: str, texts: List[str]) -> List[float]:
        """Compute similarity for multiple texts at once (more efficient)."""
        if not query or not texts:
            return [0.0] * len(texts)

        if self._use_transformer and self._model:
            return self._transformer_batch(query, texts)
        return [self._tfidf_similarity(query, t) for t in texts]

    def _transformer_similarity(self, query: str, text: str) -> float:
        """Use sentence-transformers for high-quality similarity."""
        embeddings = self._model.encode([query, text])
        # Cosine similarity
        dot = sum(a * b for a, b in zip(embeddings[0], embeddings[1]))
        norm_a = math.sqrt(sum(a * a for a in embeddings[0]))
        norm_b = math.sqrt(sum(b * b for b in embeddings[1]))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        sim = dot / (norm_a * norm_b)
        # Normalize from [-1, 1] to [0, 1]
        return max(0.0, min(1.0, (sim + 1) / 2))

    def _transformer_batch(self, query: str, texts: List[str]) -> List[float]:
        """Batch encode for efficiency."""
        all_texts = [query] + texts
        embeddings = self._model.encode(all_texts)
        query_emb = embeddings[0]

        scores = []
        norm_q = math.sqrt(sum(a * a for a in query_emb))
        if norm_q == 0:
            return [0.0] * len(texts)

        for emb in embeddings[1:]:
            dot = sum(a * b for a, b in zip(query_emb, emb))
            norm_t = math.sqrt(sum(b * b for b in emb))
            if norm_t == 0:
                scores.append(0.0)
            else:
                sim = dot / (norm_q * norm_t)
                scores.append(max(0.0, min(1.0, (sim + 1) / 2)))
        return scores

    def _tfidf_similarity(self, query: str, text: str) -> float:
        """
        TF-IDF cosine similarity fallback.

        Better than keyword overlap because:
        - Weights rare words higher (IDF)
        - Handles partial matches better
        - Normalizes by document length
        """
        query_tokens = self._tokenize(query)
        text_tokens = self._tokenize(text)

        if not query_tokens or not text_tokens:
            return 0.0

        # Build vocabulary
        all_tokens = set(query_tokens) | set(text_tokens)

        # TF vectors
        query_tf = Counter(query_tokens)
        text_tf = Counter(text_tokens)

        # With only 2 docs, standard IDF breaks (identical docs → 0).
        # Use smoothed TF-overlap instead: weight by frequency, penalize
        # words that appear in only one doc.
        query_vec = {}
        text_vec = {}
        for token in all_tokens:
            q_count = query_tf.get(token, 0)
            t_count = text_tf.get(token, 0)
            # Boost tokens present in both docs
            both = 1.5 if (q_count > 0 and t_count > 0) else 0.5
            query_vec[token] = q_count * both
            text_vec[token] = t_count * both

        # Cosine similarity
        dot = sum(query_vec[t] * text_vec[t] for t in all_tokens)
        norm_q = math.sqrt(sum(v * v for v in query_vec.values()))
        norm_t = math.sqrt(sum(v * v for v in text_vec.values()))

        if norm_q == 0 or norm_t == 0:
            return 0.0

        sim = dot / (norm_q * norm_t)
        return max(0.0, min(1.0, sim))

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization with stopword removal."""
        stopwords = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further", "then",
            "once", "and", "but", "or", "nor", "not", "so", "yet", "both",
            "each", "every", "all", "any", "few", "more", "most", "other",
            "some", "such", "no", "only", "own", "same", "than", "too", "very",
            "just", "because", "if", "when", "where", "how", "what", "which",
            "who", "whom", "this", "that", "these", "those", "it", "its",
        }
        import re
        words = re.findall(r'\b[a-z]+\b', text.lower())
        return [w for w in words if w not in stopwords and len(w) > 1]
