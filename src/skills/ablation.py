"""
Modality Ablation Skill.
Measures the individual contribution of Text, Audio, and Video.
Extracted from EvoSkills patterns.
"""

from typing import List, Dict, Callable, Any

class ExperimentGate:
    """Three-stage validation gate for code changes (CodeScientist Pattern)."""

    @staticmethod
    async def run_experiment(change_id: str, lint_fn: Callable, test_fn: Callable, backtest_fn: Callable):
        """
        Executes Mini-Pilot -> Pilot -> Full Experiment.
        Returns: {stage: str, success: bool, score: float}
        """
        # Stage 1: Mini-Pilot (Syntax/Lint)
        if not lint_fn():
            return {"stage": "mini-pilot", "success": False, "score": 0.0}
            
        # Stage 2: Pilot (Unit Tests)
        if not await test_fn():
            return {"stage": "pilot", "success": False, "score": 0.0}
            
        # Stage 3: Full Experiment (Backtest)
        accuracy = await backtest_fn()
        return {"stage": "full", "success": True, "score": accuracy}

class AblationTester:
    """Identifies redundant or low-value modality components."""

    @staticmethod
    async def run_ablation(modalities: List[str], backtest_fn: Callable) -> Dict[str, Any]:
        """Turns off each modality one at a time to measure impact."""
        # Get baseline accuracy with all modalities
        baseline = await backtest_fn(modalities)
        results = {"baseline": baseline, "contributions": {}}
        
        for mod in modalities:
            # Test without this specific modality
            subset = [m for m in modalities if m != mod]
            subset_accuracy = await backtest_fn(subset)
            
            # The drop in accuracy is that modality's contribution
            contribution = baseline - subset_accuracy
            results["contributions"][mod] = round(contribution, 4)
            
        return results
