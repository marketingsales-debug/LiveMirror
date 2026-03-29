"""
Unit tests for FineTuningLoop.
"""

import pytest
import json
import tempfile
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from src.learning.fine_tune import (
    FineTuningLoop,
    FineTuneConfig,
    FineTuneResult,
)


# =============================================================================
# MOCK COMPONENTS
# =============================================================================

class MockPrediction:
    """Mock prediction object."""
    def __init__(self, direction: float = 0.0, confidence: float = 0.5):
        self.consensus_direction = direction
        self.consensus_confidence = confidence
        self.embedding = np.random.randn(384).astype(np.float32)


class MockCrossModalLearned:
    """Mock learned attention layer."""
    def __init__(self):
        self.weights = {
            "W_q": np.random.randn(384, 384).astype(np.float32),
            "W_k": np.random.randn(384, 384).astype(np.float32),
            "W_v": np.random.randn(384, 384).astype(np.float32),
        }
    
    def get_weights(self):
        return {k: v.copy() for k, v in self.weights.items()}
    
    def set_weights(self, weights):
        self.weights = {k: v.copy() for k, v in weights.items()}


class MockPipeline:
    """Mock fusion pipeline."""
    def __init__(self):
        self.cross_modal_learned = MockCrossModalLearned()
        self._train_calls = 0
    
    def process_signal(self, content, audio_source=None, video_source=None, **kwargs):
        # Determine direction based on content keywords
        if "bullish" in content.lower() or "gain" in content.lower():
            direction = 0.5
        elif "bearish" in content.lower() or "loss" in content.lower():
            direction = -0.5
        else:
            direction = 0.0
        
        return MockPrediction(direction=direction, confidence=0.7)
    
    def fine_tune_attention(self, inputs, targets):
        self._train_calls += 1


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_pipeline():
    return MockPipeline()


@pytest.fixture
def loop(mock_pipeline):
    return FineTuningLoop(fusion_pipeline=mock_pipeline)


@pytest.fixture
def loop_with_samples(mock_pipeline):
    loop = FineTuningLoop(fusion_pipeline=mock_pipeline)
    
    # Add bullish samples (will be predicted correctly)
    for i in range(6):
        loop.add_validated_sample(
            content=f"Bullish signal {i} with gains",
            actual_direction="bullish",
            predicted_direction="bullish",
            predicted_confidence=0.8,
            platform="twitter",
        )
    
    # Add bearish samples
    for i in range(4):
        loop.add_validated_sample(
            content=f"Bearish signal {i} with losses",
            actual_direction="bearish",
            predicted_direction="bearish",
            predicted_confidence=0.75,
            platform="reddit",
        )
    
    return loop


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestFineTuneConfig:
    """Tests for FineTuneConfig."""
    
    def test_default_values(self):
        config = FineTuneConfig()
        
        assert config.learning_rate == 0.001
        assert config.min_samples_before_tune == 10
        assert config.max_samples_per_tune == 100
        assert config.tune_interval_hours == 24.0
        assert config.accuracy_threshold == 0.6
        assert config.validation_split == 0.2
        assert config.early_stopping_patience == 3
        assert config.gradient_clip == 1.0
    
    def test_custom_values(self):
        config = FineTuneConfig(
            learning_rate=0.01,
            min_samples_before_tune=20,
            accuracy_threshold=0.5,
        )
        
        assert config.learning_rate == 0.01
        assert config.min_samples_before_tune == 20
        assert config.accuracy_threshold == 0.5


# =============================================================================
# FINE-TUNE RESULT TESTS
# =============================================================================

class TestFineTuneResult:
    """Tests for FineTuneResult."""
    
    def test_improved_property_positive(self):
        result = FineTuneResult(
            tuned_at=datetime.now(),
            samples_used=50,
            pre_accuracy=0.6,
            post_accuracy=0.7,
            improvement=0.1,
            epochs_run=5,
        )
        
        assert result.improved is True
    
    def test_improved_property_negative(self):
        result = FineTuneResult(
            tuned_at=datetime.now(),
            samples_used=50,
            pre_accuracy=0.6,
            post_accuracy=0.55,
            improvement=-0.05,
            epochs_run=5,
        )
        
        assert result.improved is False
    
    def test_improved_property_zero(self):
        result = FineTuneResult(
            tuned_at=datetime.now(),
            samples_used=50,
            pre_accuracy=0.6,
            post_accuracy=0.6,
            improvement=0.0,
            epochs_run=5,
        )
        
        assert result.improved is False


# =============================================================================
# LOOP INITIALIZATION TESTS
# =============================================================================

class TestLoopInitialization:
    """Tests for FineTuningLoop initialization."""
    
    def test_create_without_pipeline(self):
        loop = FineTuningLoop()
        
        assert loop.pipeline is None
        assert loop.harness is None
        assert loop.pending_sample_count() == 0
    
    def test_create_with_pipeline(self, mock_pipeline):
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline)
        
        assert loop.pipeline is mock_pipeline
    
    def test_default_config(self, mock_pipeline):
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline)
        
        assert loop.config.learning_rate == 0.001
    
    def test_custom_config(self, mock_pipeline):
        config = FineTuneConfig(learning_rate=0.005)
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline, config=config)
        
        assert loop.config.learning_rate == 0.005


# =============================================================================
# SAMPLE MANAGEMENT TESTS
# =============================================================================

class TestSampleManagement:
    """Tests for adding and managing samples."""
    
    def test_add_sample(self, loop):
        loop.add_validated_sample(
            content="Test content",
            actual_direction="bullish",
            predicted_direction="bullish",
            predicted_confidence=0.8,
        )
        
        assert loop.pending_sample_count() == 1
    
    def test_add_multiple_samples(self, loop):
        for i in range(5):
            loop.add_validated_sample(
                content=f"Sample {i}",
                actual_direction="bullish",
                predicted_direction="bullish",
                predicted_confidence=0.7,
            )
        
        assert loop.pending_sample_count() == 5
    
    def test_sample_correctness_flagged(self, loop):
        loop.add_validated_sample(
            content="Correct prediction",
            actual_direction="bullish",
            predicted_direction="bullish",
            predicted_confidence=0.9,
        )
        
        loop.add_validated_sample(
            content="Wrong prediction",
            actual_direction="bearish",
            predicted_direction="bullish",
            predicted_confidence=0.8,
        )
        
        samples = loop._pending_samples
        assert samples[0]["is_correct"] is True
        assert samples[1]["is_correct"] is False
    
    def test_sample_metadata(self, loop):
        loop.add_validated_sample(
            content="With metadata",
            actual_direction="neutral",
            predicted_direction="neutral",
            predicted_confidence=0.5,
            platform="twitter",
            audio_source="audio.mp3",
            video_source="video.mp4",
            metadata={"author": "test_user"},
        )
        
        sample = loop._pending_samples[0]
        assert sample["platform"] == "twitter"
        assert sample["audio_source"] == "audio.mp3"
        assert sample["video_source"] == "video.mp4"
        assert sample["metadata"]["author"] == "test_user"


# =============================================================================
# SHOULD FINE-TUNE TESTS
# =============================================================================

class TestShouldFineTune:
    """Tests for should_fine_tune method."""
    
    def test_not_enough_samples(self, loop):
        for i in range(5):
            loop.add_validated_sample(
                content=f"Sample {i}",
                actual_direction="bullish",
                predicted_direction="bullish",
                predicted_confidence=0.8,
            )
        
        should_tune, reason = loop.should_fine_tune()
        
        assert should_tune is False
        assert "Need 10 samples" in reason
    
    def test_enough_samples_ready(self, loop_with_samples):
        should_tune, reason = loop_with_samples.should_fine_tune()
        
        assert should_tune is True
        assert "Ready to fine-tune" in reason
    
    def test_low_accuracy_threshold(self, loop):
        # Add mostly wrong predictions
        for i in range(10):
            loop.add_validated_sample(
                content=f"Sample {i}",
                actual_direction="bullish",
                predicted_direction="bearish",  # Wrong!
                predicted_confidence=0.8,
            )
        
        should_tune, reason = loop.should_fine_tune()
        
        assert should_tune is False
        assert "accuracy" in reason.lower()
    
    def test_time_interval_check(self, loop_with_samples):
        loop_with_samples._last_tune_at = datetime.now() - timedelta(hours=1)
        
        should_tune, reason = loop_with_samples.should_fine_tune()
        
        assert should_tune is False
        assert "since last tune" in reason


# =============================================================================
# DIRECTION TO TARGET TESTS
# =============================================================================

class TestDirectionToTarget:
    """Tests for _direction_to_target method."""
    
    def test_bullish_target(self, loop):
        target = loop._direction_to_target("bullish")
        
        assert target.shape == (384,)
        # First half should be more positive
        assert np.mean(target[:192]) > np.mean(target[192:])
    
    def test_bearish_target(self, loop):
        target = loop._direction_to_target("bearish")
        
        assert target.shape == (384,)
        # Second half should be more positive
        assert np.mean(target[192:]) > np.mean(target[:192])
    
    def test_neutral_target(self, loop):
        target = loop._direction_to_target("neutral")
        
        assert target.shape == (384,)
        # Should be all zeros
        assert np.allclose(target, 0.0)
    
    def test_targets_normalized(self, loop):
        bullish = loop._direction_to_target("bullish")
        bearish = loop._direction_to_target("bearish")
        
        # Both should be unit vectors (or zero for neutral)
        assert abs(np.linalg.norm(bullish) - 1.0) < 0.01
        assert abs(np.linalg.norm(bearish) - 1.0) < 0.01


# =============================================================================
# FINE-TUNING EXECUTION TESTS
# =============================================================================

class TestFineTuningExecution:
    """Tests for fine_tune method."""
    
    def test_fine_tune_runs(self, loop_with_samples):
        result = loop_with_samples.fine_tune()
        
        assert result is not None
        assert result.samples_used > 0
        assert result.epochs_run > 0
    
    def test_fine_tune_clears_samples(self, loop_with_samples):
        initial_count = loop_with_samples.pending_sample_count()
        
        loop_with_samples.fine_tune()
        
        # Samples should be consumed
        assert loop_with_samples.pending_sample_count() < initial_count
    
    def test_fine_tune_updates_history(self, loop_with_samples):
        assert len(loop_with_samples._tune_history) == 0
        
        loop_with_samples.fine_tune()
        
        assert len(loop_with_samples._tune_history) == 1
    
    def test_fine_tune_updates_last_tune_at(self, loop_with_samples):
        assert loop_with_samples._last_tune_at is None
        
        loop_with_samples.fine_tune()
        
        assert loop_with_samples._last_tune_at is not None
    
    def test_fine_tune_without_pipeline_raises(self):
        loop = FineTuningLoop()
        loop.add_validated_sample(
            content="Test",
            actual_direction="bullish",
            predicted_direction="bullish",
            predicted_confidence=0.8,
        )
        
        with pytest.raises(ValueError):
            loop.fine_tune()
    
    def test_maybe_fine_tune_respects_threshold(self, loop):
        # Add only 5 samples (threshold is 10)
        for i in range(5):
            loop.add_validated_sample(
                content=f"Sample {i}",
                actual_direction="bullish",
                predicted_direction="bullish",
                predicted_confidence=0.8,
            )
        
        result = loop.maybe_fine_tune()
        
        assert result is None
    
    def test_maybe_fine_tune_force(self, mock_pipeline):
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline)
        
        # Add only 2 samples
        for i in range(2):
            loop.add_validated_sample(
                content=f"Bullish sample {i}",
                actual_direction="bullish",
                predicted_direction="bullish",
                predicted_confidence=0.8,
            )
        
        result = loop.maybe_fine_tune(force=True)
        
        assert result is not None


# =============================================================================
# WEIGHT SAVE/RESTORE TESTS
# =============================================================================

class TestWeightManagement:
    """Tests for weight saving and restoration."""
    
    def test_weights_saved_before_tune(self, loop_with_samples):
        assert loop_with_samples._saved_weights is None
        
        loop_with_samples.fine_tune()
        
        # Weights should have been saved at some point
        # (even if restored due to no improvement)
    
    def test_weights_restored_on_degradation(self, mock_pipeline):
        """Test that weights are restored if accuracy degrades."""
        # This is hard to test directly, but we can verify the mechanism exists
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline)
        
        loop._save_weights()
        original_weights = loop._saved_weights.copy()
        
        # Modify weights
        mock_pipeline.cross_modal_learned.weights["W_q"] *= 2.0
        
        loop._restore_weights()
        
        # Weights should be restored
        np.testing.assert_allclose(
            mock_pipeline.cross_modal_learned.weights["W_q"],
            original_weights["W_q"]
        )


# =============================================================================
# STATISTICS TESTS
# =============================================================================

class TestStatistics:
    """Tests for stats property."""
    
    def test_initial_stats(self, loop):
        stats = loop.stats
        
        assert stats["total_tune_runs"] == 0
        assert stats["pending_samples"] == 0
        assert stats["total_improvement"] == 0.0
        assert stats["last_tune_at"] is None
    
    def test_stats_after_samples(self, loop):
        for i in range(5):
            loop.add_validated_sample(
                content=f"Sample {i}",
                actual_direction="bullish",
                predicted_direction="bullish",
                predicted_confidence=0.8,
            )
        
        stats = loop.stats
        
        assert stats["pending_samples"] == 5
    
    def test_stats_after_tune(self, loop_with_samples):
        loop_with_samples.fine_tune()
        
        stats = loop_with_samples.stats
        
        assert stats["total_tune_runs"] == 1
        assert stats["last_tune_at"] is not None


# =============================================================================
# SUMMARY TESTS
# =============================================================================

class TestSummary:
    """Tests for summary method."""
    
    def test_summary_no_history(self, loop):
        loop.add_validated_sample(
            content="Test",
            actual_direction="bullish",
            predicted_direction="bullish",
            predicted_confidence=0.8,
        )
        
        summary = loop.summary()
        
        assert "1 samples pending" in summary
        assert "no tunes run yet" in summary
    
    def test_summary_with_history(self, loop_with_samples):
        loop_with_samples.fine_tune()
        
        summary = loop_with_samples.summary()
        
        assert "FINE-TUNING SUMMARY" in summary
        assert "Total tune runs:" in summary
        assert "LAST RUN:" in summary


# =============================================================================
# EXPORT TESTS
# =============================================================================

class TestExport:
    """Tests for export_history method."""
    
    def test_export_history(self, loop_with_samples):
        loop_with_samples.fine_tune()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            loop_with_samples.export_history(temp_path)
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert "exported_at" in data
            assert data["total_tunes"] == 1
            assert len(data["history"]) == 1
            assert "pre_accuracy" in data["history"][0]
        finally:
            Path(temp_path).unlink()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for full fine-tuning workflow."""
    
    def test_full_workflow(self, mock_pipeline):
        config = FineTuneConfig(min_samples_before_tune=5)
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline, config=config)
        
        # 1. Add samples
        for i in range(6):
            loop.add_validated_sample(
                content=f"Bullish signal {i}",
                actual_direction="bullish",
                predicted_direction="bullish",
                predicted_confidence=0.8,
            )
        
        assert loop.pending_sample_count() == 6
        
        # 2. Check if should tune
        should_tune, _ = loop.should_fine_tune()
        assert should_tune is True
        
        # 3. Run fine-tuning
        result = loop.maybe_fine_tune()
        assert result is not None
        
        # 4. Verify stats updated
        stats = loop.stats
        assert stats["total_tune_runs"] == 1
        
        # 5. Add more samples (need 5 to meet threshold again)
        for i in range(6):
            loop.add_validated_sample(
                content=f"Bearish signal {i}",
                actual_direction="bearish",
                predicted_direction="bearish",
                predicted_confidence=0.7,
            )
        
        # 6. Time constraint should prevent immediate re-tune
        should_tune, reason = loop.should_fine_tune()
        assert should_tune is False
        assert "since last tune" in reason
    
    def test_multiple_tune_runs(self, mock_pipeline):
        config = FineTuneConfig(
            min_samples_before_tune=3,
            tune_interval_hours=0,  # No time limit for testing
        )
        loop = FineTuningLoop(fusion_pipeline=mock_pipeline, config=config)
        
        # Run 3 fine-tuning cycles
        for cycle in range(3):
            for i in range(4):
                loop.add_validated_sample(
                    content=f"Bullish signal {i}",
                    actual_direction="bullish",
                    predicted_direction="bullish",
                    predicted_confidence=0.8,
                )
            
            result = loop.maybe_fine_tune()
            assert result is not None
        
        assert loop.stats["total_tune_runs"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
