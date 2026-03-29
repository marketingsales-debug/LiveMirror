"""
Evolutionary Memory Module.
Stores Ideation and Experiment logs to prevent the agent from repeating mistakes.
Extracted from EvoScientist patterns.
"""

from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime

class EvolutionaryMemory:
    """Persistent logs for autonomous research evolution."""

    def __init__(self, storage_dir: str = "data/memory/evolution"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.ideation_path = os.path.join(storage_dir, "ideation.json")
        self.experiment_path = os.path.join(storage_dir, "experiments.json")
        
        # Initialize if not present
        if not os.path.exists(self.ideation_path):
            self._save([], self.ideation_path)
        if not os.path.exists(self.experiment_path):
            self._save([], self.experiment_path)

    def _load(self, path: str) -> List[Dict[str, Any]]:
        with open(path, 'r') as f:
            return json.load(f)

    def _save(self, data: List[Dict[str, Any]], path: str):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def record_hypothesis(self, hypothesis: str, worked: bool, context: str):
        """IDEATION_MEMORY: Record what ideas were proposed."""
        data = self._load(self.ideation_path)
        data.append({
            "ts": datetime.now().isoformat(),
            "hypothesis": hypothesis,
            "worked": worked,
            "context": context
        })
        self._save(data, self.ideation_path)

    def record_experiment(self, code_change: str, metric_before: float, metric_after: float, kept: bool):
        """EXPERIMENT_MEMORY: Record technical results."""
        data = self._load(self.experiment_path)
        data.append({
            "ts": datetime.now().isoformat(),
            "code_change": code_change,
            "improvement": metric_after - metric_before,
            "kept": kept
        })
        self._save(data, self.experiment_path)

    def get_recent_history(self, limit: int = 10) -> str:
        """Returns a string summary for the EMA node."""
        exps = self._load(self.experiment_path)[-limit:]
        summary = "Recent Experiments:\n"
        for e in exps:
            status = "SUCCESS" if e['improvement'] > 0 else "FAILED"
            summary += f"- {status}: {e['code_change'][:50]}... (Delta: {e['improvement']:.4f})\n"
        return summary
