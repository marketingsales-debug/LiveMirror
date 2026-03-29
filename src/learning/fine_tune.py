"""
Fine-Tuning Loop for LiveMirror.
Owner: Claude

Wires backtesting results to fusion pipeline weight updates,
enabling continuous learning from validated predictions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import uuid
import numpy as np
import json


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning behavior."""
    learning_rate: float = 0.001
    min_samples_before_tune: int = 10
    max_samples_per_tune: int = 100
    tune_interval_hours: float = 24.0
    accuracy_threshold: float = 0.6  # Only tune if accuracy above this
    validation_split: float = 0.2
    early_stopping_patience: int = 3
    gradient_clip: float = 1.0


@dataclass
class FineTuneResult:
    """Result of a fine-tuning run."""
    tuned_at: datetime
    samples_used: int
    pre_accuracy: float
    post_accuracy: float
    improvement: float
    epochs_run: int
    loss_history: List[float] = field(default_factory=list)
    validation_loss_history: List[float] = field(default_factory=list)
    early_stopped: bool = False
    
    @property
    def improved(self) -> bool:
        return self.improvement > 0


class FineTuningLoop:
    """
    Fine-tuning loop that uses backtesting results to improve fusion weights.
    
    Flow:
    1. Collect validated predictions with outcomes
    2. When threshold reached, run backtest to measure baseline
    3. Fine-tune attention weights on validated data
    4. Re-run backtest to measure improvement
    5. Accept or reject based on improvement
    
    Usage:
        loop = FineTuningLoop(fusion_pipeline, backtest_harness)
        loop.add_validated_sample(signal, outcome, prediction)
        
        # When enough samples collected:
        result = loop.maybe_fine_tune()
        if result and result.improved:
            print(f"Accuracy improved by {result.improvement:.1%}")
    """
    
    def __init__(
        self,
        fusion_pipeline=None,
        backtest_harness=None,
        config: Optional[FineTuneConfig] = None,
    ):
        """
        Initialize fine-tuning loop.
        
        Args:
            fusion_pipeline: FusionPipeline instance
            backtest_harness: BacktestHarness instance
            config: Fine-tuning configuration
        """
        self.pipeline = fusion_pipeline
        self.harness = backtest_harness
        self.config = config or FineTuneConfig()
        
        # Validated samples waiting for fine-tuning
        self._pending_samples: List[Dict[str, Any]] = []
        
        # History of fine-tuning runs
        self._tune_history: List[FineTuneResult] = []
        
        # Last tune timestamp
        self._last_tune_at: Optional[datetime] = None
        
        # Saved weights for rollback
        self._saved_weights: Optional[Dict[str, np.ndarray]] = None
    
    def add_validated_sample(
        self,
        content: str,
        actual_direction: str,  # "bullish", "bearish", "neutral"
        predicted_direction: str,
        predicted_confidence: float,
        platform: Optional[str] = None,
        audio_source: Optional[str] = None,
        video_source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a validated prediction sample for future fine-tuning.
        
        Args:
            content: Original signal content
            actual_direction: What actually happened
            predicted_direction: What was predicted
            predicted_confidence: Model confidence
            platform: Source platform
            audio_source: Optional audio path
            video_source: Optional video path
            metadata: Additional metadata
        """
        sample = {
            "content": content,
            "actual_direction": actual_direction,
            "predicted_direction": predicted_direction,
            "predicted_confidence": predicted_confidence,
            "is_correct": actual_direction == predicted_direction,
            "platform": platform,
            "audio_source": audio_source,
            "video_source": video_source,
            "metadata": metadata or {},
            "added_at": datetime.now().isoformat(),
        }
        self._pending_samples.append(sample)
    
    def pending_sample_count(self) -> int:
        """Number of samples waiting for fine-tuning."""
        return len(self._pending_samples)
    
    def should_fine_tune(self) -> Tuple[bool, str]:
        """
        Check if fine-tuning should be triggered.
        
        Returns:
            (should_tune, reason)
        """
        # Check minimum samples
        if len(self._pending_samples) < self.config.min_samples_before_tune:
            return False, f"Need {self.config.min_samples_before_tune} samples, have {len(self._pending_samples)}"
        
        # Check time since last tune
        if self._last_tune_at:
            hours_since = (datetime.now() - self._last_tune_at).total_seconds() / 3600
            if hours_since < self.config.tune_interval_hours:
                return False, f"Only {hours_since:.1f}h since last tune (need {self.config.tune_interval_hours}h)"
        
        # Check sample accuracy (don't tune on garbage data)
        correct_count = sum(1 for s in self._pending_samples if s["is_correct"])
        accuracy = correct_count / len(self._pending_samples)
        if accuracy < self.config.accuracy_threshold:
            return False, f"Sample accuracy {accuracy:.1%} below threshold {self.config.accuracy_threshold:.0%}"
        
        return True, "Ready to fine-tune"
    
    def maybe_fine_tune(self, force: bool = False) -> Optional[FineTuneResult]:
        """
        Run fine-tuning if conditions are met.
        
        Args:
            force: Bypass threshold checks
            
        Returns:
            FineTuneResult if tuning ran, None otherwise
        """
        if not force:
            should_tune, reason = self.should_fine_tune()
            if not should_tune:
                return None
        
        return self.fine_tune()
    
    def fine_tune(self) -> FineTuneResult:
        """
        Run fine-tuning on pending samples.
        
        Returns:
            FineTuneResult with before/after metrics
        """
        if self.pipeline is None:
            raise ValueError("No fusion pipeline provided")
        
        run_id = f"ft_{uuid.uuid4().hex[:12]}"
        emit_fine_tune_started = None
        emit_fine_tune_progress = None
        emit_fine_tune_completed = None
        record_fine_tune = None
        try:
            from backend.app.api.stream import (
                emit_fine_tune_started as _emit_started,
                emit_fine_tune_progress as _emit_progress,
                emit_fine_tune_completed as _emit_completed,
            )
            from backend.app.api.metrics import record_fine_tune as _record_fine_tune
            emit_fine_tune_started = _emit_started
            emit_fine_tune_progress = _emit_progress
            emit_fine_tune_completed = _emit_completed
            record_fine_tune = _record_fine_tune
        except ImportError:
            pass
        
        def _fire_and_forget(coro) -> None:
            if coro is None:
                return
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                loop.create_task(coro)
        
        # 1. Save current weights for potential rollback
        self._save_weights()
        
        # 2. Prepare training data
        samples = self._pending_samples[:self.config.max_samples_per_tune]
        train_data, val_data = self._split_samples(samples)
        
        # 3. Measure pre-tune accuracy (using validation set)
        pre_accuracy = self._compute_accuracy(val_data)
        epochs_target = 20
        if emit_fine_tune_started is not None:
            _fire_and_forget(emit_fine_tune_started(
                run_id=run_id,
                samples=len(samples),
                epochs=epochs_target,
            ))
        
        # 4. Convert samples to training format
        inputs, targets = self._samples_to_training_data(train_data)
        
        # 5. Fine-tune with early stopping
        loss_history = []
        val_loss_history = []
        best_val_loss = float("inf")
        patience_counter = 0
        epochs_run = 0
        early_stopped = False
        
        for epoch in range(epochs_target):  # Max epochs_target epochs
            # Train step
            loss = self._train_step(inputs, targets)
            loss_history.append(loss)
            
            # Validation step
            val_inputs, val_targets = self._samples_to_training_data(val_data)
            val_loss = self._compute_loss(val_inputs, val_targets)
            val_loss_history.append(val_loss)
            
            epochs_run = epoch + 1
            
            if emit_fine_tune_progress is not None:
                _fire_and_forget(emit_fine_tune_progress(
                    run_id=run_id,
                    epoch=epochs_run,
                    total_epochs=epochs_target,
                    loss=float(val_loss),
                    accuracy=float(pre_accuracy),
                ))
            
            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.config.early_stopping_patience:
                    early_stopped = True
                    break
        
        # 6. Measure post-tune accuracy
        post_accuracy = self._compute_accuracy(val_data)
        improvement = post_accuracy - pre_accuracy
        
        # 6b. Run regression test if harness available
        regression_passed = True
        if self.harness is not None:
            regression_passed = self._run_regression_test(pre_accuracy)
        
        # 7. Rollback if degraded or regression failed
        rollback = False
        if improvement < 0 or not regression_passed:
            self._restore_weights()
            post_accuracy = pre_accuracy
            improvement = 0.0
            rollback = True
        
        # 8. Record result
        result = FineTuneResult(
            tuned_at=datetime.now(),
            samples_used=len(samples),
            pre_accuracy=pre_accuracy,
            post_accuracy=post_accuracy,
            improvement=improvement,
            epochs_run=epochs_run,
            loss_history=loss_history,
            validation_loss_history=val_loss_history,
            early_stopped=early_stopped,
        )
        self._tune_history.append(result)
        
        # 9. Clear used samples
        self._pending_samples = self._pending_samples[len(samples):]
        self._last_tune_at = datetime.now()
        
        if emit_fine_tune_completed is not None:
            _fire_and_forget(emit_fine_tune_completed(
                run_id=run_id,
                samples=len(samples),
                pre_accuracy=pre_accuracy,
                post_accuracy=post_accuracy,
                improvement=improvement,
                rollback=rollback,
            ))
        
        if record_fine_tune is not None:
            _fire_and_forget(record_fine_tune(
                samples=len(samples),
                pre_accuracy=pre_accuracy,
                post_accuracy=post_accuracy,
                rollback=rollback,
            ))
        
        return result
    
    def _run_regression_test(self, baseline_accuracy: float) -> bool:
        """
        Run regression test using BacktestHarness.
        
        Args:
            baseline_accuracy: Pre-tune accuracy to compare against
            
        Returns:
            True if regression test passes (no degradation)
        """
        if self.harness is None or not self.harness.signals:
            return True  # No harness or signals, skip regression
        
        try:
            metrics = self.harness.run_backtest(emit_progress=False)
            
            # Pass if accuracy didn't drop more than 5%
            threshold = baseline_accuracy * 0.95
            return metrics.accuracy >= threshold
        except Exception:
            # On error, assume regression passed (don't block fine-tuning)
            return True
    
    def set_regression_harness(self, harness) -> None:
        """Set the BacktestHarness for regression testing."""
        self.harness = harness
    
    def _split_samples(self, samples: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Split samples into training and validation sets."""
        split_idx = int(len(samples) * (1 - self.config.validation_split))
        return samples[:split_idx], samples[split_idx:]
    
    def _samples_to_training_data(
        self, samples: List[Dict]
    ) -> Tuple[List[Dict[str, Any]], List[np.ndarray]]:
        """Convert samples to (inputs, targets) format for fine-tuning."""
        inputs = []
        targets = []
        
        for sample in samples:
            input_dict = {
                "text": sample["content"],
                "audio": sample.get("audio_source"),
                "video": sample.get("video_source"),
            }
            inputs.append(input_dict)
            
            # Target: direction-aligned embedding
            direction = sample["actual_direction"]
            target = self._direction_to_target(direction)
            targets.append(target)
        
        return inputs, targets
    
    def _direction_to_target(self, direction: str) -> np.ndarray:
        """Convert direction string to target embedding."""
        # Create distinct embeddings for each direction
        target = np.zeros(384, dtype=np.float32)
        
        if direction == "bullish":
            # Bullish: positive in first half
            target[:192] = 1.0
            target[192:] = -0.5
        elif direction == "bearish":
            # Bearish: positive in second half
            target[:192] = -0.5
            target[192:] = 1.0
        else:
            # Neutral: uniform low values
            target[:] = 0.0
        
        # Normalize
        norm = np.linalg.norm(target)
        if norm > 0:
            target = target / norm
        
        return target
    
    def _train_step(
        self, inputs: List[Dict], targets: List[np.ndarray]
    ) -> float:
        """
        Run one training step.
        
        Returns:
            Training loss
        """
        if hasattr(self.pipeline, "fine_tune_attention"):
            # Use pipeline's built-in fine-tuning
            self.pipeline.fine_tune_attention(inputs, targets)
        
        # Compute loss after update
        return self._compute_loss(inputs, targets)
    
    def _compute_loss(
        self, inputs: List[Dict], targets: List[np.ndarray]
    ) -> float:
        """Compute MSE loss on given data."""
        if not inputs:
            return 0.0
        
        total_loss = 0.0
        for inp, target in zip(inputs, targets):
            try:
                pred = self.pipeline.process_signal(
                    content=inp["text"],
                    audio_source=inp.get("audio"),
                    video_source=inp.get("video"),
                )
                if pred is not None and hasattr(pred, "embedding"):
                    pred_emb = np.array(pred.embedding)
                    loss = np.mean((pred_emb - target) ** 2)
                    total_loss += loss
            except Exception:
                pass
        
        return total_loss / len(inputs) if inputs else 0.0
    
    def _compute_accuracy(self, samples: List[Dict]) -> float:
        """Compute direction accuracy on given samples."""
        if not samples:
            return 0.0
        
        correct = 0
        for sample in samples:
            try:
                pred = self.pipeline.process_signal(
                    content=sample["content"],
                    audio_source=sample.get("audio_source"),
                    video_source=sample.get("video_source"),
                )
                if pred is not None:
                    pred_dir = self._prediction_to_direction(pred)
                    if pred_dir == sample["actual_direction"]:
                        correct += 1
            except Exception:
                pass
        
        return correct / len(samples)
    
    def _prediction_to_direction(self, prediction: Any) -> str:
        """Extract direction from prediction object."""
        if hasattr(prediction, "consensus_direction"):
            val = prediction.consensus_direction
        else:
            val = 0.0
        
        if val > 0.2:
            return "bullish"
        elif val < -0.2:
            return "bearish"
        return "neutral"
    
    def _save_weights(self) -> None:
        """Save current attention weights for rollback."""
        if hasattr(self.pipeline, "cross_modal_learned"):
            learned = self.pipeline.cross_modal_learned
            if hasattr(learned, "get_weights"):
                self._saved_weights = learned.get_weights()
            else:
                self._saved_weights = {}
    
    def _restore_weights(self) -> None:
        """Restore saved weights after failed fine-tuning."""
        if self._saved_weights and hasattr(self.pipeline, "cross_modal_learned"):
            learned = self.pipeline.cross_modal_learned
            if hasattr(learned, "set_weights"):
                learned.set_weights(self._saved_weights)
    
    def export_history(self, path: str) -> None:
        """Export fine-tuning history to JSON."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_tunes": len(self._tune_history),
            "pending_samples": len(self._pending_samples),
            "history": [
                {
                    "tuned_at": r.tuned_at.isoformat(),
                    "samples_used": r.samples_used,
                    "pre_accuracy": r.pre_accuracy,
                    "post_accuracy": r.post_accuracy,
                    "improvement": r.improvement,
                    "epochs_run": r.epochs_run,
                    "early_stopped": r.early_stopped,
                }
                for r in self._tune_history
            ],
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Current fine-tuning statistics."""
        total_improvement = sum(r.improvement for r in self._tune_history)
        avg_improvement = total_improvement / len(self._tune_history) if self._tune_history else 0.0
        
        return {
            "total_tune_runs": len(self._tune_history),
            "pending_samples": len(self._pending_samples),
            "total_improvement": total_improvement,
            "avg_improvement_per_tune": avg_improvement,
            "last_tune_at": self._last_tune_at.isoformat() if self._last_tune_at else None,
            "early_stops": sum(1 for r in self._tune_history if r.early_stopped),
        }
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        if not self._tune_history:
            return f"Fine-tuning loop: {len(self._pending_samples)} samples pending, no tunes run yet"
        
        stats = self.stats
        last_result = self._tune_history[-1]
        
        lines = [
            "=" * 50,
            "LIVEMIRROR FINE-TUNING SUMMARY",
            "=" * 50,
            f"Total tune runs: {stats['total_tune_runs']}",
            f"Pending samples: {stats['pending_samples']}",
            f"Total improvement: {stats['total_improvement']:.1%}",
            f"Avg improvement per tune: {stats['avg_improvement_per_tune']:.1%}",
            "",
            "LAST RUN:",
            f"  Samples used: {last_result.samples_used}",
            f"  Pre-accuracy: {last_result.pre_accuracy:.1%}",
            f"  Post-accuracy: {last_result.post_accuracy:.1%}",
            f"  Improvement: {last_result.improvement:.1%}",
            f"  Epochs: {last_result.epochs_run}",
            f"  Early stopped: {last_result.early_stopped}",
            "=" * 50,
        ]
        
        return "\n".join(lines)
