"""
Tests for semantic embeddings scorer.
Owner: Claude
"""

import pytest
from src.ingestion.embeddings import SemanticScorer


class TestSemanticScorer:
    def setup_method(self):
        self.scorer = SemanticScorer()

    def test_identical_text_high_similarity(self):
        score = self.scorer.similarity("AI regulation", "AI regulation")
        assert score > 0.8

    def test_related_text_moderate_similarity(self):
        # TF-IDF can only match on shared words, not synonyms
        score = self.scorer.similarity(
            "AI regulation policy",
            "AI regulation and government policy on technology"
        )
        assert score > 0.1  # shared words: AI, regulation, policy

    def test_unrelated_text_low_similarity(self):
        score = self.scorer.similarity(
            "AI regulation policy",
            "chocolate cake recipe with frosting"
        )
        related = self.scorer.similarity(
            "AI regulation policy",
            "AI regulation and technology policy"
        )
        assert score < related

    def test_empty_text_returns_zero(self):
        assert self.scorer.similarity("", "test") == 0.0
        assert self.scorer.similarity("test", "") == 0.0

    def test_batch_similarity(self):
        texts = ["AI policy", "chocolate cake", "machine learning law"]
        scores = self.scorer.batch_similarity("AI regulation", texts)
        assert len(scores) == 3
        # AI policy should score higher than chocolate cake
        assert scores[0] > scores[1]

    def test_score_bounded(self):
        score = self.scorer.similarity("test query", "test document content")
        assert 0.0 <= score <= 1.0

    def test_tfidf_handles_stopwords(self):
        """TF-IDF should weight content words over stopwords."""
        score_relevant = self.scorer._tfidf_similarity(
            "bitcoin price", "bitcoin price prediction for march"
        )
        score_irrelevant = self.scorer._tfidf_similarity(
            "bitcoin price", "the weather is nice today"
        )
        assert score_relevant > score_irrelevant
