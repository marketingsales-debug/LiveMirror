"""
Experiment framework for production hardening.
Owner: Claude

Supports:
- Shadow mode (duplicate runs, no user impact)
- A/B routing (percentage of traffic to candidate variant)
"""

from dataclasses import dataclass
import hashlib
import os
from typing import Optional


def _get_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


@dataclass
class ExperimentConfig:
    shadow_mode_enabled: bool = False
    ab_test_enabled: bool = False
    ab_split: float = 0.1  # 10% traffic to candidate
    ab_seed: str = "livemirror"
    force_variant: Optional[str] = None
    candidate_agent_count: Optional[int] = None
    candidate_simulation_rounds: Optional[int] = None

    @staticmethod
    def from_env() -> "ExperimentConfig":
        return ExperimentConfig(
            shadow_mode_enabled=_get_bool(os.getenv("SHADOW_MODE_ENABLED"), False),
            ab_test_enabled=_get_bool(os.getenv("AB_TEST_ENABLED"), False),
            ab_split=_get_float(os.getenv("AB_TEST_SPLIT"), 0.1),
            ab_seed=os.getenv("AB_TEST_SEED", "livemirror"),
            force_variant=os.getenv("AB_FORCE_VARIANT"),
            candidate_agent_count=_get_int(os.getenv("AB_CANDIDATE_AGENT_COUNT")),
            candidate_simulation_rounds=_get_int(os.getenv("AB_CANDIDATE_SIMULATION_ROUNDS")),
        )


class ExperimentManager:
    def __init__(self, config: Optional[ExperimentConfig] = None):
        self.config = config or ExperimentConfig()

    @staticmethod
    def from_env() -> "ExperimentManager":
        return ExperimentManager(ExperimentConfig.from_env())

    @property
    def shadow_mode(self) -> bool:
        return self.config.shadow_mode_enabled

    @property
    def ab_enabled(self) -> bool:
        return self.config.ab_test_enabled and not self.config.shadow_mode_enabled

    def assign_variant(self, key: str) -> str:
        if self.config.force_variant in {"control", "candidate"}:
            return self.config.force_variant
        if not self.ab_enabled:
            return "control"
        bucket = self._hash_to_unit_interval(key)
        return "candidate" if bucket < self.config.ab_split else "control"

    def candidate_agent_count(self, default: int) -> int:
        return self.config.candidate_agent_count or default

    def candidate_simulation_rounds(self, default: int) -> int:
        return self.config.candidate_simulation_rounds or default

    def _hash_to_unit_interval(self, key: str) -> float:
        h = hashlib.sha256(f"{self.config.ab_seed}:{key}".encode("utf-8")).digest()
        return int.from_bytes(h[:4], "big") / 2**32
