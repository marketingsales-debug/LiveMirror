"""
Platform type definitions shared across all layers.
LOCK REQUIRED to edit this file — see .collab/RULES.md Rule 3.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


class Platform(str, Enum):
    """Supported data platforms."""
    REDDIT = "reddit"
    TWITTER = "twitter"
    BLUESKY = "bluesky"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    HACKERNEWS = "hackernews"
    POLYMARKET = "polymarket"
    WEB = "web"
    NEWS = "news"
    MOLTBOOK = "moltbook"  # AI agent social network


class SignalType(str, Enum):
    """Types of external signals."""
    SOCIAL_POST = "social_post"
    COMMENT = "comment"
    REACTION = "reaction"
    SHARE = "share"
    PREDICTION_MARKET = "prediction_market"
    NEWS_ARTICLE = "news_article"
    ECONOMIC = "economic"
    GOVERNMENT = "government"
    SENSOR = "sensor"


@dataclass
class RawSignal:
    """A single piece of data from any platform."""
    platform: Platform
    signal_type: SignalType
    content: str
    id: Optional[str] = None  # Unique identifier for the signal
    author: Optional[str] = None
    url: Optional[str] = None
    timestamp: Optional[datetime] = None
    engagement: Dict[str, int] = field(default_factory=dict)  # likes, shares, comments
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Generate ID if not provided."""
        if self.id is None:
            import hashlib
            content_hash = hashlib.md5(self.content[:100].encode()).hexdigest()[:8]
            platform_prefix = self.platform.value[:3]
            self.id = f"{platform_prefix}_{content_hash}"

    def engagement_score(self) -> float:
        """Composite engagement score."""
        likes = self.engagement.get("likes", 0)
        shares = self.engagement.get("shares", 0)
        comments = self.engagement.get("comments", 0)
        return likes + (shares * 3) + (comments * 2)


@dataclass
class ScoredSignal:
    """A signal after relevance scoring."""
    signal: RawSignal
    relevance_score: float = 0.0       # 0-1, text similarity to query
    engagement_velocity: float = 0.0    # engagement per hour
    recency_score: float = 0.0          # 0-1, newer = higher
    cross_platform_score: float = 0.0   # 0-1, appears on multiple platforms
    composite_score: float = 0.0        # weighted final score

    def compute_composite(
        self,
        relevance_weight: float = 0.35,
        engagement_weight: float = 0.25,
        recency_weight: float = 0.20,
        cross_platform_weight: float = 0.20,
    ) -> float:
        self.composite_score = (
            self.relevance_score * relevance_weight
            + self.engagement_velocity * engagement_weight
            + self.recency_score * recency_weight
            + self.cross_platform_score * cross_platform_weight
        )
        return self.composite_score
