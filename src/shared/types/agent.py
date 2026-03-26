"""
Agent type definitions shared across simulation and analysis layers.
LOCK REQUIRED to edit this file — see .collab/RULES.md Rule 3.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    """Agent roles in simulation."""
    INDIVIDUAL = "individual"
    INFLUENCER = "influencer"
    MEDIA = "media"
    ORGANIZATION = "organization"
    GOVERNMENT = "government"
    EXPERT = "expert"
    BOT = "bot"


class Stance(str, Enum):
    """Agent stance on topics."""
    SUPPORTIVE = "supportive"
    OPPOSING = "opposing"
    NEUTRAL = "neutral"
    OBSERVER = "observer"


@dataclass
class BehavioralFingerprint:
    """
    Derived from REAL observed behavior, not LLM imagination.
    Updated by the learning layer as real data comes in.
    """
    avg_posts_per_day: float = 0.0
    avg_response_time_minutes: float = 0.0
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 23)))
    sentiment_distribution: Dict[str, float] = field(
        default_factory=lambda: {"positive": 0.33, "neutral": 0.34, "negative": 0.33}
    )
    preferred_platforms: List[str] = field(default_factory=list)
    influence_radius: float = 1.0  # how many people typically see their content
    echo_chamber_score: float = 0.5  # 0 = diverse connections, 1 = total echo chamber
    persuadability: float = 0.5  # 0 = stubborn, 1 = easily influenced
    data_source: str = "inferred"  # "real_data" | "inferred" | "llm_generated"
    last_calibrated: Optional[datetime] = None


@dataclass
class AgentPersona:
    """Full agent definition for simulation."""
    agent_id: int
    name: str
    role: AgentRole
    entity_type: str

    # Behavioral config
    activity_level: float = 0.5  # 0-1
    stance: Stance = Stance.NEUTRAL
    sentiment_bias: float = 0.0  # -1 to 1
    influence_weight: float = 1.0

    # Behavioral fingerprint (from real data when available)
    fingerprint: BehavioralFingerprint = field(default_factory=BehavioralFingerprint)

    # Evolution tracking
    belief_history: List[Dict[str, Any]] = field(default_factory=list)
    trust_network: Dict[int, float] = field(default_factory=dict)  # agent_id -> trust score

    # Memory
    memory_summary: str = ""
    interaction_count: int = 0

    def update_trust(self, other_agent_id: int, delta: float):
        current = self.trust_network.get(other_agent_id, 0.5)
        self.trust_network[other_agent_id] = max(0.0, min(1.0, current + delta))
