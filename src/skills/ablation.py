"""
Modality Ablation Skill.
Measures the individual contribution of Text, Audio, and Video.
Extracted from EvoSkills patterns.
"""

from typing import List, Dict, Callable, Any

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
