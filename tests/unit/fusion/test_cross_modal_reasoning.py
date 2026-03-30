"""
Unit tests for CrossModalReasoning.
Owner: Claude

Tests cross-modal conflict detection, pairwise analysis, and deception patterns.
"""

import pytest
import numpy as np
from src.fusion.reasoning import (
    CrossModalReasoning,
    ConflictType,
    PairwiseConflict,
    CrossModalConflictReport,
)


def make_embedding(seed: int = 0) -> np.ndarray:
    """Create a deterministic 384-dim embedding."""
    rng = np.random.default_rng(seed)
    emb = rng.standard_normal(384).astype(np.float32)
    return emb / np.linalg.norm(emb)


def make_similar_embedding(base: np.ndarray, noise: float = 0.1) -> np.ndarray:
    """Create an embedding similar to base with some noise."""
    rng = np.random.default_rng(42)
    noisy = base + rng.standard_normal(384).astype(np.float32) * noise
    return (noisy / np.linalg.norm(noisy)).astype(np.float32)


def make_opposite_embedding(base: np.ndarray) -> np.ndarray:
    """Create an embedding opposite to base."""
    return (-base).astype(np.float32)


class TestCrossModalReasoning:
    """Test CrossModalReasoning conflict detection."""

    def test_single_modality_returns_no_conflict(self):
        """Single modality should return full alignment."""
        reasoning = CrossModalReasoning()
        embeddings = {"text": make_embedding(1)}
        
        report = reasoning.compute_modality_alignment(embeddings)
        
        assert report["alignment"] == 1.0
        assert report["conflict"] == 0.0
        assert report["modalities_used"] == ["text"]

    def test_similar_embeddings_high_alignment(self):
        """Similar embeddings should show high alignment."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        embeddings = {
            "text": base,
            "audio": make_similar_embedding(base, noise=0.05),
        }
        
        report = reasoning.compute_modality_alignment(embeddings)
        
        assert report["alignment"] > 0.7
        assert report["conflict"] < 0.3

    def test_opposite_embeddings_high_conflict(self):
        """Opposite embeddings should show high conflict."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        embeddings = {
            "text": base,
            "audio": make_opposite_embedding(base),
        }
        
        report = reasoning.compute_modality_alignment(embeddings)
        
        assert report["conflict"] > 0.8
        assert report["alignment"] < 0.2

    def test_pairwise_conflicts_computed(self):
        """Pairwise conflicts should be computed for all pairs."""
        reasoning = CrossModalReasoning()
        embeddings = {
            "text": make_embedding(1),
            "audio": make_embedding(2),
            "video": make_embedding(3),
        }
        
        pairwise = reasoning.compute_pairwise_conflicts(embeddings)
        
        # 3 modalities = 3 pairs: text-audio, text-video, audio-video
        assert len(pairwise) == 3
        assert all(isinstance(pc, PairwiseConflict) for pc in pairwise)

    def test_cosine_similarity_handles_invalid_vectors(self):
        """Cosine similarity should guard empty or non-finite values."""
        reasoning = CrossModalReasoning()

        empty = np.array([], dtype=np.float32)
        assert reasoning._cosine_similarity(empty, empty) == 0.0

        nan_vec = np.array([np.nan, 1.0], dtype=np.float32)
        inf_vec = np.array([np.inf, 0.0], dtype=np.float32)
        assert reasoning._cosine_similarity(nan_vec, inf_vec) == 0.0

    def test_analyze_cross_modal_conflict_full_report(self):
        """Full conflict analysis should return comprehensive report."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        embeddings = {
            "text": base,
            "audio": make_opposite_embedding(base),
            "video": make_similar_embedding(base, noise=0.2),
        }
        
        report = reasoning.analyze_cross_modal_conflict(embeddings, text_sentiment=0.8)
        
        assert isinstance(report, CrossModalConflictReport)
        assert 0.0 <= report.overall_alignment <= 1.0
        assert 0.0 <= report.overall_conflict <= 1.0
        assert len(report.pairwise_conflicts) == 3
        assert report.dominant_conflict_type in ConflictType
        assert 0.0 <= report.manipulation_risk <= 1.0
        assert len(report.modalities_analyzed) == 3

    def test_detect_deception_pattern_bullish_text_nervous_audio(self):
        """Bullish text + conflicting audio should detect deception."""
        reasoning = CrossModalReasoning()
        text_emb = make_embedding(1)
        audio_emb = make_opposite_embedding(text_emb)
        
        result = reasoning.detect_ceo_deception_pattern(
            text_embedding=text_emb,
            audio_embedding=audio_emb,
            text_sentiment=0.8,
        )
        
        assert result["deception_detected"] is True
        assert result["confidence"] > 0.7
        assert result["pattern"] == "bullish_words_nervous_tone"

    def test_detect_deception_pattern_bullish_text_hesitant_video(self):
        """Bullish text + conflicting video should detect deception."""
        reasoning = CrossModalReasoning()
        text_emb = make_embedding(1)
        video_emb = make_opposite_embedding(text_emb)
        
        result = reasoning.detect_ceo_deception_pattern(
            text_embedding=text_emb,
            video_embedding=video_emb,
            text_sentiment=0.7,
        )
        
        assert result["deception_detected"] is True
        assert result["confidence"] > 0.6
        assert result["pattern"] == "bullish_words_hesitant_body"

    def test_no_deception_when_modalities_align(self):
        """Aligned modalities should not trigger deception detection."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        
        result = reasoning.detect_ceo_deception_pattern(
            text_embedding=base,
            audio_embedding=make_similar_embedding(base, noise=0.1),
            video_embedding=make_similar_embedding(base, noise=0.15),
            text_sentiment=0.8,
        )
        
        assert result["deception_detected"] is False

    def test_insufficient_modalities_for_deception(self):
        """Single modality should not allow deception detection."""
        reasoning = CrossModalReasoning()
        
        result = reasoning.detect_ceo_deception_pattern(
            text_embedding=make_embedding(1),
            text_sentiment=0.9,
        )
        
        assert result["deception_detected"] is False
        assert "Insufficient" in result["reasoning"]

    def test_conflict_type_classification_text_audio(self):
        """Text-audio conflict should be classified correctly."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        embeddings = {
            "text": base,
            "audio": make_opposite_embedding(base),
        }
        
        pairwise = reasoning.compute_pairwise_conflicts(embeddings)
        
        assert len(pairwise) == 1
        pc = pairwise[0]
        assert pc.conflict_type in [ConflictType.DECEPTION, ConflictType.INCONSISTENCY]
        assert "text" in [pc.modality_a, pc.modality_b]
        assert "audio" in [pc.modality_a, pc.modality_b]

    def test_manipulation_risk_elevated_for_deception(self):
        """Deception conflicts should elevate manipulation risk."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        embeddings = {
            "text": base,
            "audio": make_opposite_embedding(base),
        }
        
        report = reasoning.analyze_cross_modal_conflict(embeddings, text_sentiment=0.9)
        
        assert report.manipulation_risk > 0.5

    def test_confidence_penalty_for_high_conflict(self):
        """High conflict should result in confidence penalty."""
        reasoning = CrossModalReasoning()
        base = make_embedding(1)
        embeddings = {
            "text": base,
            "audio": make_opposite_embedding(base),
            "video": make_opposite_embedding(base),
        }
        
        report = reasoning.analyze_cross_modal_conflict(embeddings)
        
        assert report.confidence_penalty > 0.0

    def test_final_prediction_applies_penalty(self):
        """Final prediction should apply confidence penalty."""
        reasoning = CrossModalReasoning()
        
        class MockPrediction:
            consensus_confidence = 0.8
            metadata = {}
        
        pred = MockPrediction()
        alignment_report = {"alignment": 0.2, "conflict": 0.8}
        
        result = reasoning.final_prediction_with_reasoning(pred, alignment_report)
        
        assert result.consensus_confidence < 0.8
        assert "reasoning" in result.metadata

    def test_final_prediction_applies_boost(self):
        """Final prediction should apply confidence boost for high alignment."""
        reasoning = CrossModalReasoning()
        
        class MockPrediction:
            consensus_confidence = 0.7
            metadata = {}
        
        pred = MockPrediction()
        alignment_report = {"alignment": 0.95, "conflict": 0.05}
        
        result = reasoning.final_prediction_with_reasoning(pred, alignment_report)
        
        assert result.consensus_confidence > 0.7
        assert result.consensus_confidence <= 0.99

    def test_detect_modality_conflict_bullish_high_conflict(self):
        """Bullish text with high conflict should flag manipulation."""
        reasoning = CrossModalReasoning()
        
        result = reasoning.detect_modality_conflict(
            alignment_report={"conflict": 0.75},
            text_sentiment=0.85,
        )
        
        assert result["likely_manipulation"] is True
        assert result["confidence"] > 0.8

    def test_detect_modality_conflict_bearish_high_conflict(self):
        """Bearish text with high conflict should flag manipulation."""
        reasoning = CrossModalReasoning()
        
        result = reasoning.detect_modality_conflict(
            alignment_report={"conflict": 0.75},
            text_sentiment=-0.85,
        )
        
        assert result["likely_manipulation"] is True
        assert "bearish" in result["type"].lower()
