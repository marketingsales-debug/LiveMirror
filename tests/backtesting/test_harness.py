"""
Unit tests for BacktestHarness.
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.backtesting.harness import (
    BacktestHarness,
    BacktestResult,
    BacktestMetrics,
    HistoricalSignal,
    OutcomeDirection,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def harness():
    """Create a BacktestHarness instance without a pipeline."""
    return BacktestHarness(fusion_pipeline=None)


@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline that returns predictable results."""
    class MockPrediction:
        def __init__(self, content):
            self.consensus_direction = 0.5 if "bullish" in content.lower() else -0.5 if "bearish" in content.lower() else 0.0
            self.consensus_confidence = 0.75
            self.metadata = {"reasoning": {"conflict": 0.1}}
            self.text_embedding = [0.1] * 384
            self.audio_embedding = None
            self.video_embedding = None
            self.sentiment_embedding = [0.2] * 384
    
    class MockPipeline:
        def process_signal(self, content, **kwargs):
            return MockPrediction(content)
    
    return MockPipeline()


@pytest.fixture
def sample_signals():
    """Generate sample historical signals for testing."""
    return [
        HistoricalSignal(
            signal_id="sig_001",
            content="Strong earnings report, stock up 10%",
            platform="twitter",
            timestamp=datetime.now() - timedelta(days=30),
            engagement={"likes": 500, "retweets": 100},
            actual_outcome=OutcomeDirection.BULLISH,
            outcome_magnitude=0.8,
        ),
        HistoricalSignal(
            signal_id="sig_002",
            content="Company announces major layoffs",
            platform="reddit",
            timestamp=datetime.now() - timedelta(days=25),
            engagement={"upvotes": 1000, "comments": 200},
            actual_outcome=OutcomeDirection.BEARISH,
            outcome_magnitude=0.7,
        ),
        HistoricalSignal(
            signal_id="sig_003",
            content="Market consolidating ahead of Fed meeting",
            platform="hackernews",
            timestamp=datetime.now() - timedelta(days=20),
            engagement={"points": 300, "comments": 50},
            actual_outcome=OutcomeDirection.NEUTRAL,
            outcome_magnitude=0.2,
        ),
    ]


# =============================================================================
# HISTORICAL SIGNAL TESTS
# =============================================================================

class TestHistoricalSignal:
    """Tests for HistoricalSignal dataclass."""
    
    def test_create_basic_signal(self):
        """Test creating a basic historical signal."""
        signal = HistoricalSignal(
            signal_id="test_001",
            content="Test content",
            platform="twitter",
            timestamp=datetime.now(),
        )
        assert signal.signal_id == "test_001"
        assert signal.content == "Test content"
        assert signal.platform == "twitter"
        assert signal.actual_outcome == OutcomeDirection.NEUTRAL  # default
    
    def test_create_full_signal(self):
        """Test creating a signal with all fields."""
        ts = datetime.now()
        outcome_ts = ts + timedelta(hours=24)
        
        signal = HistoricalSignal(
            signal_id="test_002",
            content="Bullish news",
            platform="youtube",
            timestamp=ts,
            engagement={"likes": 1000, "comments": 50},
            actual_outcome=OutcomeDirection.BULLISH,
            outcome_timestamp=outcome_ts,
            outcome_magnitude=0.85,
            audio_source="audio.mp3",
            video_source="video.mp4",
            metadata={"author": "analyst_1"},
        )
        
        assert signal.actual_outcome == OutcomeDirection.BULLISH
        assert signal.outcome_magnitude == 0.85
        assert signal.audio_source == "audio.mp3"
        assert signal.video_source == "video.mp4"
        assert signal.metadata["author"] == "analyst_1"
    
    def test_outcome_direction_values(self):
        """Test OutcomeDirection enum values."""
        assert OutcomeDirection.BULLISH.value == "bullish"
        assert OutcomeDirection.BEARISH.value == "bearish"
        assert OutcomeDirection.NEUTRAL.value == "neutral"


# =============================================================================
# BACKTEST RESULT TESTS
# =============================================================================

class TestBacktestResult:
    """Tests for BacktestResult dataclass."""
    
    def test_create_correct_result(self):
        """Test creating a correct prediction result."""
        result = BacktestResult(
            signal_id="sig_001",
            predicted_direction="bullish",
            predicted_confidence=0.8,
            actual_direction="bullish",
            actual_magnitude=0.75,
            is_correct=True,
            direction_error=0.0,
            confidence_error=0.2,
        )
        
        assert result.is_correct is True
        assert result.direction_error == 0.0
    
    def test_create_wrong_result(self):
        """Test creating an incorrect prediction result."""
        result = BacktestResult(
            signal_id="sig_002",
            predicted_direction="bullish",
            predicted_confidence=0.7,
            actual_direction="bearish",
            actual_magnitude=0.8,
            is_correct=False,
            direction_error=2.0,  # opposite direction
            confidence_error=0.7,
        )
        
        assert result.is_correct is False
        assert result.direction_error == 2.0
    
    def test_modalities_default_empty(self):
        """Test that modalities_used defaults to empty list."""
        result = BacktestResult(
            signal_id="sig_003",
            predicted_direction="neutral",
            predicted_confidence=0.5,
            actual_direction="neutral",
            actual_magnitude=0.1,
        )
        
        assert result.modalities_used == []


# =============================================================================
# BACKTEST METRICS TESTS
# =============================================================================

class TestBacktestMetrics:
    """Tests for BacktestMetrics dataclass."""
    
    def test_default_metrics(self):
        """Test default metric values."""
        metrics = BacktestMetrics()
        
        assert metrics.total_predictions == 0
        assert metrics.correct_predictions == 0
        assert metrics.accuracy == 0.0
        assert metrics.calibration_error == 0.0
    
    def test_metrics_with_values(self):
        """Test metrics with populated values."""
        metrics = BacktestMetrics(
            total_predictions=100,
            correct_predictions=75,
            accuracy=0.75,
            precision_bullish=0.8,
            recall_bullish=0.7,
            f1_bullish=0.746,
            calibration_error=0.05,
            brier_score=0.15,
        )
        
        assert metrics.accuracy == 0.75
        assert metrics.f1_bullish == 0.746
        assert metrics.brier_score == 0.15


# =============================================================================
# HARNESS INITIALIZATION TESTS
# =============================================================================

class TestHarnessInitialization:
    """Tests for BacktestHarness initialization."""
    
    def test_create_without_pipeline(self):
        """Test creating harness without a pipeline."""
        harness = BacktestHarness()
        
        assert harness.pipeline is None
        assert harness.signals == []
        assert harness.results == []
    
    def test_create_with_pipeline(self, mock_pipeline):
        """Test creating harness with a mock pipeline."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        
        assert harness.pipeline is mock_pipeline


# =============================================================================
# SYNTHETIC SIGNAL GENERATION TESTS
# =============================================================================

class TestSyntheticSignalGeneration:
    """Tests for generate_synthetic_signals method."""
    
    def test_generate_default_count(self, harness):
        """Test generating default number of signals."""
        count = harness.generate_synthetic_signals(count=100)
        
        assert count == 100
        assert len(harness.signals) == 100
    
    def test_generate_with_seed(self, harness):
        """Test reproducibility with seed."""
        harness1 = BacktestHarness()
        harness2 = BacktestHarness()
        
        harness1.generate_synthetic_signals(count=50, seed=42)
        harness2.generate_synthetic_signals(count=50, seed=42)
        
        # Same seed should produce same signals
        for s1, s2 in zip(harness1.signals, harness2.signals):
            assert s1.content == s2.content
            assert s1.actual_outcome == s2.actual_outcome
    
    def test_generate_different_seeds(self, harness):
        """Test different seeds produce different signals."""
        harness1 = BacktestHarness()
        harness2 = BacktestHarness()
        
        harness1.generate_synthetic_signals(count=20, seed=42)
        harness2.generate_synthetic_signals(count=20, seed=99)
        
        # Different seeds should produce different signals
        different_count = sum(
            1 for s1, s2 in zip(harness1.signals, harness2.signals)
            if s1.content != s2.content
        )
        assert different_count > 0
    
    def test_bullish_ratio(self, harness):
        """Test bullish outcome ratio is approximately correct."""
        harness.generate_synthetic_signals(count=1000, seed=42, bullish_ratio=0.5, bearish_ratio=0.3)
        
        bullish_count = sum(1 for s in harness.signals if s.actual_outcome == OutcomeDirection.BULLISH)
        bearish_count = sum(1 for s in harness.signals if s.actual_outcome == OutcomeDirection.BEARISH)
        neutral_count = sum(1 for s in harness.signals if s.actual_outcome == OutcomeDirection.NEUTRAL)
        
        # Allow 10% margin
        assert 400 <= bullish_count <= 600
        assert 200 <= bearish_count <= 400
        assert 100 <= neutral_count <= 300
    
    def test_all_platforms_covered(self, harness):
        """Test signals are generated across all platforms."""
        harness.generate_synthetic_signals(count=500, seed=42)
        
        platforms = set(s.platform for s in harness.signals)
        expected_platforms = {"twitter", "reddit", "hackernews", "youtube", "tiktok"}
        
        assert platforms == expected_platforms
    
    def test_engagement_generated(self, harness):
        """Test engagement metrics are generated."""
        harness.generate_synthetic_signals(count=10, seed=42)
        
        for signal in harness.signals:
            assert "likes" in signal.engagement
            assert "comments" in signal.engagement
            assert "shares" in signal.engagement
            assert signal.engagement["likes"] > 0


# =============================================================================
# JSON LOADING TESTS
# =============================================================================

class TestJsonLoading:
    """Tests for load_historical_signals method."""
    
    def test_load_from_file(self, harness):
        """Test loading signals from JSON file."""
        data = [
            {
                "signal_id": "json_001",
                "content": "Test bullish signal",
                "platform": "twitter",
                "timestamp": "2024-01-15T10:30:00Z",
                "engagement": {"likes": 500},
                "actual_outcome": "bullish",
                "outcome_magnitude": 0.8,
            },
            {
                "signal_id": "json_002",
                "content": "Test bearish signal",
                "platform": "reddit",
                "timestamp": "2024-01-16T14:00:00Z",
                "actual_outcome": "bearish",
                "outcome_magnitude": 0.6,
            },
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            count = harness.load_historical_signals(temp_path)
            
            assert count == 2
            assert len(harness.signals) == 2
            assert harness.signals[0].signal_id == "json_001"
            assert harness.signals[0].actual_outcome == OutcomeDirection.BULLISH
            assert harness.signals[1].actual_outcome == OutcomeDirection.BEARISH
        finally:
            Path(temp_path).unlink()
    
    def test_load_with_optional_fields(self, harness):
        """Test loading signals with optional fields."""
        data = [
            {
                "signal_id": "json_003",
                "content": "Multimodal signal",
                "platform": "youtube",
                "timestamp": "2024-02-01T08:00:00Z",
                "audio_source": "audio.mp3",
                "video_source": "video.mp4",
                "metadata": {"author": "analyst_x"},
            },
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            harness.load_historical_signals(temp_path)
            
            signal = harness.signals[0]
            assert signal.audio_source == "audio.mp3"
            assert signal.video_source == "video.mp4"
            assert signal.metadata["author"] == "analyst_x"
        finally:
            Path(temp_path).unlink()


# =============================================================================
# BACKTEST EXECUTION TESTS (WITH MOCK PIPELINE)
# =============================================================================

class TestBacktestExecution:
    """Tests for run_backtest method with mock pipeline."""
    
    def test_run_backtest_synthetic(self, mock_pipeline):
        """Test running backtest on synthetic signals."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        harness.generate_synthetic_signals(count=50, seed=42)
        
        metrics = harness.run_backtest(emit_progress=False)
        
        assert metrics.total_predictions > 0
        assert 0.0 <= metrics.accuracy <= 1.0
        assert len(harness.results) > 0
    
    def test_results_populated(self, mock_pipeline):
        """Test that results are populated after backtest."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        harness.generate_synthetic_signals(count=20, seed=42)
        
        harness.run_backtest(emit_progress=False)
        
        assert len(harness.results) == 20
        for result in harness.results:
            assert result.signal_id.startswith("synth_")
            assert result.predicted_direction in ["bullish", "bearish", "neutral"]
            assert 0.0 <= result.predicted_confidence <= 1.0
    
    def test_confusion_matrix_populated(self, mock_pipeline):
        """Test confusion matrix is computed."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        harness.generate_synthetic_signals(count=100, seed=42)
        
        metrics = harness.run_backtest(emit_progress=False)
        
        # At least some of the confusion matrix entries should be non-zero
        total_matrix = (
            metrics.true_bullish +
            metrics.true_bearish +
            metrics.true_neutral +
            metrics.false_bullish +
            metrics.false_bearish +
            metrics.false_neutral
        )
        assert total_matrix > 0


# =============================================================================
# METRICS COMPUTATION TESTS
# =============================================================================

class TestMetricsComputation:
    """Tests for metrics computation."""
    
    def test_accuracy_computation(self):
        """Test accuracy is computed correctly."""
        harness = BacktestHarness()
        harness.results = [
            BacktestResult("s1", "bullish", 0.8, "bullish", 0.7, is_correct=True),
            BacktestResult("s2", "bearish", 0.7, "bearish", 0.6, is_correct=True),
            BacktestResult("s3", "bullish", 0.6, "bearish", 0.8, is_correct=False),
            BacktestResult("s4", "neutral", 0.5, "neutral", 0.2, is_correct=True),
        ]
        
        metrics = harness._compute_metrics(0.0)
        
        assert metrics.total_predictions == 4
        assert metrics.correct_predictions == 3
        assert metrics.accuracy == 0.75
    
    def test_precision_recall_computation(self):
        """Test precision and recall are computed correctly."""
        harness = BacktestHarness()
        # 2 true bullish, 1 false bullish
        harness.results = [
            BacktestResult("s1", "bullish", 0.8, "bullish", 0.7, is_correct=True),
            BacktestResult("s2", "bullish", 0.7, "bullish", 0.6, is_correct=True),
            BacktestResult("s3", "bullish", 0.6, "bearish", 0.8, is_correct=False),
        ]
        
        harness.signals = [
            HistoricalSignal("s1", "c1", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BULLISH),
            HistoricalSignal("s2", "c2", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BULLISH),
            HistoricalSignal("s3", "c3", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BEARISH),
        ]
        
        metrics = harness._compute_metrics(0.0)
        
        # Precision = true_bullish / pred_bullish = 2/3
        assert abs(metrics.precision_bullish - 0.6667) < 0.01
        # Recall = true_bullish / actual_bullish = 2/2 = 1.0
        assert metrics.recall_bullish == 1.0
    
    def test_calibration_error(self):
        """Test calibration error computation."""
        harness = BacktestHarness()
        harness.results = [
            BacktestResult("s1", "bullish", 0.9, "bullish", 0.7, is_correct=True),
            BacktestResult("s2", "bullish", 0.8, "bearish", 0.6, is_correct=False),
        ]
        
        metrics = harness._compute_metrics(0.0)
        
        # Mean confidence = 0.85, accuracy = 0.5
        assert abs(metrics.mean_confidence - 0.85) < 0.01
        assert metrics.accuracy == 0.5
        assert abs(metrics.calibration_error - 0.35) < 0.01


# =============================================================================
# EXPORT TESTS
# =============================================================================

class TestExport:
    """Tests for export_results method."""
    
    def test_export_results(self, mock_pipeline):
        """Test exporting results to JSON."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        harness.generate_synthetic_signals(count=10, seed=42)
        harness.run_backtest(emit_progress=False)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            harness.export_results(temp_path)
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert "generated_at" in data
            assert data["signal_count"] == 10
            assert data["result_count"] == 10
            assert len(data["results"]) == 10
        finally:
            Path(temp_path).unlink()


# =============================================================================
# SUMMARY TESTS
# =============================================================================

class TestSummary:
    """Tests for summary method."""
    
    def test_summary_no_results(self, harness):
        """Test summary when no results available."""
        summary = harness.summary()
        
        assert "No backtest results available" in summary
    
    def test_summary_with_results(self, mock_pipeline):
        """Test summary with results."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        harness.generate_synthetic_signals(count=50, seed=42)
        harness.run_backtest(emit_progress=False)
        
        summary = harness.summary()
        
        assert "LIVEMIRROR BACKTESTING RESULTS" in summary
        assert "Total Predictions:" in summary
        assert "DIRECTION ACCURACY:" in summary
        assert "CALIBRATION:" in summary
        assert "CONFUSION MATRIX:" in summary


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_signals_backtest(self, mock_pipeline):
        """Test running backtest with no signals."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        
        metrics = harness.run_backtest(emit_progress=False)
        
        assert metrics.total_predictions == 0
        assert metrics.accuracy == 0.0
    
    def test_single_signal_backtest(self, mock_pipeline):
        """Test running backtest with single signal."""
        harness = BacktestHarness(fusion_pipeline=mock_pipeline)
        harness.signals = [
            HistoricalSignal(
                signal_id="single",
                content="Bullish signal",
                platform="twitter",
                timestamp=datetime.now(),
                actual_outcome=OutcomeDirection.BULLISH,
            )
        ]
        
        metrics = harness.run_backtest(emit_progress=False)
        
        assert metrics.total_predictions == 1
    
    def test_all_correct_predictions(self, mock_pipeline):
        """Test with all correct predictions (100% accuracy)."""
        class PerfectPipeline:
            def process_signal(self, content, **kwargs):
                class Pred:
                    consensus_direction = 0.5  # bullish
                    consensus_confidence = 0.9
                    metadata = {}
                    text_embedding = [0.1] * 384
                return Pred()
        
        harness = BacktestHarness(fusion_pipeline=PerfectPipeline())
        harness.signals = [
            HistoricalSignal("s1", "content", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BULLISH),
            HistoricalSignal("s2", "content", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BULLISH),
        ]
        
        metrics = harness.run_backtest(emit_progress=False)
        
        assert metrics.accuracy == 1.0
        assert metrics.correct_predictions == 2
    
    def test_all_wrong_predictions(self, mock_pipeline):
        """Test with all wrong predictions (0% accuracy)."""
        class WrongPipeline:
            def process_signal(self, content, **kwargs):
                class Pred:
                    consensus_direction = 0.5  # bullish
                    consensus_confidence = 0.9
                    metadata = {}
                    text_embedding = [0.1] * 384
                return Pred()
        
        harness = BacktestHarness(fusion_pipeline=WrongPipeline())
        harness.signals = [
            HistoricalSignal("s1", "content", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BEARISH),
            HistoricalSignal("s2", "content", "twitter", datetime.now(), actual_outcome=OutcomeDirection.BEARISH),
        ]
        
        metrics = harness.run_backtest(emit_progress=False)
        
        assert metrics.accuracy == 0.0
        assert metrics.correct_predictions == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
