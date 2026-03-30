"""
Backtesting Harness for LiveMirror.
Owner: Claude

Replays historical signals through the fusion pipeline and compares
predictions against real outcomes to compute accuracy metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import json
import numpy as np


class OutcomeDirection(Enum):
    """Actual market/narrative outcome."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class HistoricalSignal:
    """A historical signal with known outcome."""
    signal_id: str
    content: str
    platform: str
    timestamp: datetime
    engagement: Dict[str, int] = field(default_factory=dict)
    
    # Ground truth
    actual_outcome: OutcomeDirection = OutcomeDirection.NEUTRAL
    outcome_timestamp: Optional[datetime] = None
    outcome_magnitude: float = 0.0  # How strong was the move (0-1)
    
    # Optional multimodal sources
    audio_source: Optional[str] = None
    video_source: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    """Result of a single backtest prediction."""
    signal_id: str
    predicted_direction: str
    predicted_confidence: float
    actual_direction: str
    actual_magnitude: float
    
    # Computed metrics
    is_correct: bool = False
    direction_error: float = 0.0  # 0 = perfect, 2 = opposite
    confidence_error: float = 0.0  # |predicted_confidence - accuracy|
    
    # Additional data
    manipulation_risk: float = 0.0
    modalities_used: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


@dataclass
class BacktestMetrics:
    """Aggregate metrics from backtesting."""
    total_predictions: int = 0
    correct_predictions: int = 0
    
    # Direction accuracy
    accuracy: float = 0.0
    precision_bullish: float = 0.0
    recall_bullish: float = 0.0
    precision_bearish: float = 0.0
    recall_bearish: float = 0.0
    f1_bullish: float = 0.0
    f1_bearish: float = 0.0
    
    # Calibration
    mean_confidence: float = 0.0
    mean_accuracy: float = 0.0
    calibration_error: float = 0.0  # |mean_confidence - accuracy|
    brier_score: float = 0.0  # Mean squared error of confidence
    
    # Timing
    avg_processing_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Breakdown
    results_by_platform: Dict[str, Dict[str, float]] = field(default_factory=dict)
    results_by_modality_count: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    # Confusion matrix
    true_bullish: int = 0
    false_bullish: int = 0
    true_bearish: int = 0
    false_bearish: int = 0
    true_neutral: int = 0
    false_neutral: int = 0


class BacktestHarness:
    """
    Backtesting harness for the LiveMirror fusion pipeline.
    
    Usage:
        harness = BacktestHarness(pipeline)
        harness.load_historical_signals("path/to/signals.json")
        # or
        harness.generate_synthetic_signals(count=1000)
        
        metrics = harness.run_backtest()
        print(metrics.accuracy, metrics.calibration_error)
    """
    
    def __init__(self, fusion_pipeline=None):
        """
        Initialize backtesting harness.
        
        Args:
            fusion_pipeline: FusionPipeline instance (optional, will create if None)
        """
        self.pipeline = fusion_pipeline
        self.signals: List[HistoricalSignal] = []
        self.results: List[BacktestResult] = []
        
    def _ensure_pipeline(self):
        """Lazy-load pipeline if not provided."""
        if self.pipeline is None:
            from ..fusion.pipeline import FusionPipeline
            self.pipeline = FusionPipeline()
    
    def load_historical_signals(self, path: str) -> int:
        """
        Load historical signals from JSON file.
        
        Expected format:
        [
            {
                "signal_id": "sig_001",
                "content": "Bitcoin reaching new highs...",
                "platform": "twitter",
                "timestamp": "2024-01-15T10:30:00Z",
                "engagement": {"likes": 500, "retweets": 100},
                "actual_outcome": "bullish",
                "outcome_magnitude": 0.8
            },
            ...
        ]
        
        Returns:
            Number of signals loaded
        """
        with open(path, "r") as f:
            data = json.load(f)
        
        for item in data:
            signal = HistoricalSignal(
                signal_id=item["signal_id"],
                content=item["content"],
                platform=item["platform"],
                timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                engagement=item.get("engagement", {}),
                actual_outcome=OutcomeDirection(item.get("actual_outcome", "neutral")),
                outcome_magnitude=item.get("outcome_magnitude", 0.5),
                audio_source=item.get("audio_source"),
                video_source=item.get("video_source"),
                metadata=item.get("metadata", {}),
            )
            self.signals.append(signal)
        
        return len(self.signals)
    
    def generate_synthetic_signals(
        self,
        count: int = 100,
        seed: int = 42,
        bullish_ratio: float = 0.4,
        bearish_ratio: float = 0.4,
    ) -> int:
        """
        Generate synthetic historical signals for testing.
        
        Args:
            count: Number of signals to generate
            seed: Random seed for reproducibility
            bullish_ratio: Proportion of bullish outcomes
            bearish_ratio: Proportion of bearish outcomes
            
        Returns:
            Number of signals generated
        """
        rng = np.random.default_rng(seed)
        
        platforms = ["twitter", "reddit", "hackernews", "youtube", "tiktok"]
        
        bullish_templates = [
            "Strong earnings report exceeds expectations by {pct}%",
            "Major partnership announced with {company}",
            "Institutional buying pressure increasing",
            "Technical breakout above key resistance",
            "Positive regulatory developments emerging",
            "Record revenue growth reported",
            "Expansion into new markets announced",
        ]
        
        bearish_templates = [
            "Disappointing quarterly results miss estimates",
            "Key executive departures announced",
            "Regulatory investigation opened",
            "Technical breakdown below support levels",
            "Credit downgrade warning issued",
            "Supply chain disruptions reported",
            "Competitive threats emerging from {company}",
        ]
        
        neutral_templates = [
            "Company maintains guidance for the quarter",
            "Trading volume remains average",
            "Market awaiting upcoming earnings report",
            "Consolidation phase continues",
            "Mixed signals from economic data",
        ]
        
        companies = ["Microsoft", "Apple", "Google", "Amazon", "Meta", "Tesla"]
        
        for i in range(count):
            # Determine outcome
            r = rng.random()
            if r < bullish_ratio:
                outcome = OutcomeDirection.BULLISH
                template = rng.choice(bullish_templates)
                magnitude = 0.5 + rng.random() * 0.5
            elif r < bullish_ratio + bearish_ratio:
                outcome = OutcomeDirection.BEARISH
                template = rng.choice(bearish_templates)
                magnitude = 0.5 + rng.random() * 0.5
            else:
                outcome = OutcomeDirection.NEUTRAL
                template = rng.choice(neutral_templates)
                magnitude = rng.random() * 0.3
            
            # Fill template
            content = template.format(
                pct=rng.integers(10, 50),
                company=rng.choice(companies),
            )
            
            # Generate engagement
            base_engagement = rng.integers(100, 10000)
            engagement = {
                "likes": int(base_engagement),
                "comments": int(base_engagement * rng.uniform(0.05, 0.2)),
                "shares": int(base_engagement * rng.uniform(0.01, 0.1)),
            }
            
            signal = HistoricalSignal(
                signal_id=f"synth_{i:04d}",
                content=content,
                platform=rng.choice(platforms),
                timestamp=datetime.now() - timedelta(days=int(rng.integers(1, 365))),
                engagement=engagement,
                actual_outcome=outcome,
                outcome_magnitude=round(magnitude, 3),
            )
            self.signals.append(signal)
        
        return count
    
    def _direction_from_prediction(self, prediction: Any) -> str:
        """Extract direction string from prediction result."""
        if hasattr(prediction, "consensus_direction"):
            val = prediction.consensus_direction
        elif isinstance(prediction, dict):
            val = prediction.get("consensus_direction", 0.0)
        else:
            val = 0.0
        
        if val > 0.2:
            return "bullish"
        elif val < -0.2:
            return "bearish"
        return "neutral"
    
    def _confidence_from_prediction(self, prediction: Any) -> float:
        """Extract confidence from prediction result."""
        if hasattr(prediction, "consensus_confidence"):
            return prediction.consensus_confidence
        elif isinstance(prediction, dict):
            return prediction.get("consensus_confidence", 0.5)
        return 0.5
    
    def run_backtest(
        self,
        batch_size: int = 16,
        emit_progress: bool = True,
    ) -> BacktestMetrics:
        """
        Run backtest on all loaded signals.
        
        Args:
            batch_size: Number of signals to process in parallel
            emit_progress: Whether to emit progress updates
            
        Returns:
            BacktestMetrics with aggregate statistics
        """
        self._ensure_pipeline()
        self.results = []
        
        total_time_start = datetime.now()
        
        # Process signals
        for i, signal in enumerate(self.signals):
            t0 = datetime.now()
            
            try:
                # Run through fusion pipeline
                prediction = self.pipeline.process_signal(
                    content=signal.content,
                    audio_source=signal.audio_source,
                    video_source=signal.video_source,
                    platform=signal.platform,
                    engagement=signal.engagement,
                    metadata={"signal_id": signal.signal_id},
                )
                
                if prediction is None:
                    continue
                
                # Extract prediction details
                pred_direction = self._direction_from_prediction(prediction)
                pred_confidence = self._confidence_from_prediction(prediction)
                actual_direction = signal.actual_outcome.value
                
                # Compute correctness
                is_correct = pred_direction == actual_direction
                
                # Direction error: 0 = correct, 1 = neutral vs directional, 2 = opposite
                if pred_direction == actual_direction:
                    direction_error = 0.0
                elif pred_direction == "neutral" or actual_direction == "neutral":
                    direction_error = 1.0
                else:
                    direction_error = 2.0
                
                # Confidence error
                accuracy_as_confidence = 1.0 if is_correct else 0.0
                confidence_error = abs(pred_confidence - accuracy_as_confidence)
                
                # Manipulation risk from reasoning
                manipulation_risk = 0.0
                if hasattr(prediction, "metadata") and prediction.metadata:
                    reasoning = prediction.metadata.get("reasoning", {})
                    manipulation_risk = reasoning.get("conflict", 0.0)
                
                # Modalities used
                modalities = []
                for mod in ["text", "audio", "video", "sentiment"]:
                    if hasattr(prediction, f"{mod}_embedding") and getattr(prediction, f"{mod}_embedding") is not None:
                        modalities.append(mod)
                
                processing_time = (datetime.now() - t0).total_seconds() * 1000
                
                result = BacktestResult(
                    signal_id=signal.signal_id,
                    predicted_direction=pred_direction,
                    predicted_confidence=pred_confidence,
                    actual_direction=actual_direction,
                    actual_magnitude=signal.outcome_magnitude,
                    is_correct=is_correct,
                    direction_error=direction_error,
                    confidence_error=confidence_error,
                    manipulation_risk=manipulation_risk,
                    modalities_used=modalities,
                    processing_time_ms=processing_time,
                )
                self.results.append(result)
                
            except Exception as e:
                if emit_progress:
                    print(f"Error processing signal {signal.signal_id}: {e}")
                continue
            
            if emit_progress and (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(self.signals)} signals")
        
        total_time = (datetime.now() - total_time_start).total_seconds() * 1000
        
        # Compute metrics
        return self._compute_metrics(total_time)
    
    def _compute_metrics(self, total_time_ms: float) -> BacktestMetrics:
        """Compute aggregate metrics from results."""
        if not self.results:
            return BacktestMetrics()
        
        metrics = BacktestMetrics(
            total_predictions=len(self.results),
            total_time_ms=total_time_ms,
        )
        
        # Basic accuracy
        metrics.correct_predictions = sum(1 for r in self.results if r.is_correct)
        metrics.accuracy = metrics.correct_predictions / metrics.total_predictions
        
        # Confusion matrix
        for r in self.results:
            if r.actual_direction == "bullish":
                if r.predicted_direction == "bullish":
                    metrics.true_bullish += 1
                else:
                    metrics.false_bearish += 1 if r.predicted_direction == "bearish" else 0
            elif r.actual_direction == "bearish":
                if r.predicted_direction == "bearish":
                    metrics.true_bearish += 1
                else:
                    metrics.false_bullish += 1 if r.predicted_direction == "bullish" else 0
            else:
                if r.predicted_direction == "neutral":
                    metrics.true_neutral += 1
                else:
                    metrics.false_neutral += 1
        
        # Precision/Recall for bullish
        pred_bullish = sum(1 for r in self.results if r.predicted_direction == "bullish")
        actual_bullish = sum(1 for r in self.results if r.actual_direction == "bullish")
        if pred_bullish > 0:
            metrics.precision_bullish = metrics.true_bullish / pred_bullish
        if actual_bullish > 0:
            metrics.recall_bullish = metrics.true_bullish / actual_bullish
        if metrics.precision_bullish + metrics.recall_bullish > 0:
            metrics.f1_bullish = 2 * (metrics.precision_bullish * metrics.recall_bullish) / (
                metrics.precision_bullish + metrics.recall_bullish
            )
        
        # Precision/Recall for bearish
        pred_bearish = sum(1 for r in self.results if r.predicted_direction == "bearish")
        actual_bearish = sum(1 for r in self.results if r.actual_direction == "bearish")
        if pred_bearish > 0:
            metrics.precision_bearish = metrics.true_bearish / pred_bearish
        if actual_bearish > 0:
            metrics.recall_bearish = metrics.true_bearish / actual_bearish
        if metrics.precision_bearish + metrics.recall_bearish > 0:
            metrics.f1_bearish = 2 * (metrics.precision_bearish * metrics.recall_bearish) / (
                metrics.precision_bearish + metrics.recall_bearish
            )
        
        # Calibration
        confidences = [r.predicted_confidence for r in self.results]
        accuracies = [1.0 if r.is_correct else 0.0 for r in self.results]
        
        metrics.mean_confidence = np.mean(confidences)
        metrics.mean_accuracy = metrics.accuracy
        metrics.calibration_error = abs(metrics.mean_confidence - metrics.accuracy)
        
        # Brier score (mean squared error of probability estimates)
        brier_scores = []
        for r in self.results:
            # For each outcome class
            actual_bullish = 1.0 if r.actual_direction == "bullish" else 0.0
            pred_bullish_prob = r.predicted_confidence if r.predicted_direction == "bullish" else 0.0
            brier_scores.append((pred_bullish_prob - actual_bullish) ** 2)
        metrics.brier_score = np.mean(brier_scores)
        
        # Timing
        processing_times = [r.processing_time_ms for r in self.results]
        metrics.avg_processing_time_ms = np.mean(processing_times)
        
        # Breakdown by platform
        platforms = set(s.platform for s in self.signals)
        for platform in platforms:
            platform_results = [
                r for r, s in zip(self.results, self.signals[:len(self.results)])
                if s.platform == platform
            ]
            if platform_results:
                correct = sum(1 for r in platform_results if r.is_correct)
                metrics.results_by_platform[platform] = {
                    "count": len(platform_results),
                    "accuracy": correct / len(platform_results),
                    "avg_confidence": np.mean([r.predicted_confidence for r in platform_results]),
                }
        
        # Breakdown by modality count
        for r in self.results:
            mod_count = len(r.modalities_used)
            if mod_count not in metrics.results_by_modality_count:
                metrics.results_by_modality_count[mod_count] = {
                    "count": 0,
                    "correct": 0,
                }
            metrics.results_by_modality_count[mod_count]["count"] += 1
            if r.is_correct:
                metrics.results_by_modality_count[mod_count]["correct"] += 1
        
        for mod_count in metrics.results_by_modality_count:
            data = metrics.results_by_modality_count[mod_count]
            data["accuracy"] = data["correct"] / data["count"] if data["count"] > 0 else 0.0
        
        return metrics
    
    def export_results(self, path: str) -> None:
        """Export backtest results to JSON file."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "signal_count": len(self.signals),
            "result_count": len(self.results),
            "results": [
                {
                    "signal_id": r.signal_id,
                    "predicted_direction": r.predicted_direction,
                    "predicted_confidence": r.predicted_confidence,
                    "actual_direction": r.actual_direction,
                    "is_correct": r.is_correct,
                    "direction_error": r.direction_error,
                    "confidence_error": r.confidence_error,
                    "manipulation_risk": r.manipulation_risk,
                    "modalities_used": r.modalities_used,
                    "processing_time_ms": r.processing_time_ms,
                }
                for r in self.results
            ],
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def summary(self) -> str:
        """Generate human-readable summary of backtest results."""
        if not self.results:
            return "No backtest results available. Run run_backtest() first."
        
        metrics = self._compute_metrics(0.0)
        
        lines = [
            "=" * 60,
            "LIVEMIRROR BACKTESTING RESULTS",
            "=" * 60,
            f"Total Predictions: {metrics.total_predictions}",
            f"Correct: {metrics.correct_predictions} ({metrics.accuracy:.1%})",
            "",
            "DIRECTION ACCURACY:",
            f"  Bullish - Precision: {metrics.precision_bullish:.1%}, Recall: {metrics.recall_bullish:.1%}, F1: {metrics.f1_bullish:.3f}",
            f"  Bearish - Precision: {metrics.precision_bearish:.1%}, Recall: {metrics.recall_bearish:.1%}, F1: {metrics.f1_bearish:.3f}",
            "",
            "CALIBRATION:",
            f"  Mean Confidence: {metrics.mean_confidence:.1%}",
            f"  Actual Accuracy: {metrics.accuracy:.1%}",
            f"  Calibration Error: {metrics.calibration_error:.3f}",
            f"  Brier Score: {metrics.brier_score:.4f}",
            "",
            "CONFUSION MATRIX:",
            f"  True Bullish: {metrics.true_bullish}",
            f"  True Bearish: {metrics.true_bearish}",
            f"  True Neutral: {metrics.true_neutral}",
            "",
            "PERFORMANCE:",
            f"  Avg Processing Time: {metrics.avg_processing_time_ms:.1f}ms",
            "",
        ]
        
        if metrics.results_by_platform:
            lines.append("BY PLATFORM:")
            for platform, data in sorted(metrics.results_by_platform.items()):
                lines.append(f"  {platform}: {data['accuracy']:.1%} ({data['count']} signals)")
        
        if metrics.results_by_modality_count:
            lines.append("")
            lines.append("BY MODALITY COUNT:")
            for mod_count, data in sorted(metrics.results_by_modality_count.items()):
                lines.append(f"  {mod_count} modalities: {data['accuracy']:.1%} ({data['count']} signals)")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
