"""
Agent Factory — creates simulation agents from knowledge graph entities.
Owner: Claude

Converts knowledge graph entities (people, orgs, media outlets) into
AgentPersona instances with behavioral fingerprints. When real behavioral
data is available (from the learning layer), it's used to calibrate the
fingerprints. Otherwise, role-based defaults are used.
"""

import random
from typing import List, Optional, Dict
from datetime import datetime

from ...shared.types import (
    AgentPersona, AgentRole, Stance, BehavioralFingerprint, ScoredSignal,
)
from ...graph.knowledge.graph import KnowledgeGraph, Entity, EntityType


# Map entity types → agent roles
ENTITY_ROLE_MAP: Dict[EntityType, AgentRole] = {
    EntityType.PERSON:       AgentRole.INDIVIDUAL,
    EntityType.ORGANIZATION: AgentRole.ORGANIZATION,
    EntityType.TOPIC:        AgentRole.INDIVIDUAL,
    EntityType.PRODUCT:      AgentRole.ORGANIZATION,
    EntityType.LOCATION:     AgentRole.INDIVIDUAL,
    EntityType.EVENT:        AgentRole.MEDIA,
    EntityType.ASSET:        AgentRole.INDIVIDUAL,
}

# Role-based default activity levels
ROLE_ACTIVITY: Dict[AgentRole, float] = {
    AgentRole.INDIVIDUAL:   0.30,
    AgentRole.INFLUENCER:   0.70,
    AgentRole.MEDIA:        0.85,
    AgentRole.ORGANIZATION: 0.50,
    AgentRole.GOVERNMENT:   0.40,
    AgentRole.EXPERT:       0.45,
    AgentRole.BOT:          0.95,
}

# Role-based default influence weights
ROLE_INFLUENCE: Dict[AgentRole, float] = {
    AgentRole.INDIVIDUAL:   0.5,
    AgentRole.INFLUENCER:   2.5,
    AgentRole.MEDIA:        3.0,
    AgentRole.ORGANIZATION: 2.0,
    AgentRole.GOVERNMENT:   2.5,
    AgentRole.EXPERT:       1.8,
    AgentRole.BOT:          0.4,
}

# Mention count thresholds for role promotion
INFLUENCER_THRESHOLD = 20  # entities mentioned 20+ times → influencer
MEDIA_THRESHOLD = 50        # entities mentioned 50+ times → media


def _stance_from_sentiment(avg_sentiment: float) -> Stance:
    """Convert average sentiment score to agent stance."""
    if avg_sentiment >= 0.2:
        return Stance.SUPPORTIVE
    elif avg_sentiment <= -0.2:
        return Stance.OPPOSING
    return Stance.NEUTRAL


def _influence_from_mentions(mention_count: int, cross_platform: int) -> float:
    """
    Compute influence weight from graph statistics.
    More mentions + more platforms = more influential.
    """
    base = min(3.0, 0.5 + (mention_count / 20.0))
    platform_boost = min(1.5, cross_platform * 0.3)
    return min(4.0, base + platform_boost)


class AgentFactory:
    """
    Creates AgentPersona instances from knowledge graph data.

    Usage:
        factory = AgentFactory()
        agents = factory.from_graph(graph, query="AI regulation", max_agents=50)
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._next_id = 0

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def from_graph(
        self,
        graph: KnowledgeGraph,
        query: str,
        max_agents: int = 50,
        bot_ratio: float = 0.10,
        scored_signals: Optional[List[ScoredSignal]] = None,
    ) -> List[AgentPersona]:
        """
        Create agents from knowledge graph entities.

        Args:
            graph:           Populated knowledge graph
            query:           Topic query — used to extract relevant subgraph
            max_agents:      Maximum number of agents to create
            bot_ratio:       Fraction of agents that are synthetic bots (0.0–0.3)
            scored_signals:  Optional scored signals for behavioral calibration

        Returns:
            List of AgentPersona ready for simulation
        """
        # Extract relevant entities from graph
        subgraph = graph.get_narrative_subgraph(query, max_depth=2)
        entities = subgraph.get("entities", [])

        # Fall back to top entities if subgraph empty
        if not entities:
            entities = graph.get_top_entities(limit=max_agents)

        # Cap entity count
        entity_count = min(len(entities), int(max_agents * (1.0 - bot_ratio)))
        entities = entities[:entity_count]

        agents: List[AgentPersona] = []

        # Create agents from entities
        for entity in entities:
            agent = self.create_from_entity(entity, graph)
            agents.append(agent)

        # Inject synthetic bot agents
        bot_count = max_agents - len(agents)
        if bot_count > 0:
            bots = self._create_bots(bot_count, sentiment_bias=0.0)
            agents.extend(bots)

        # Initialize trust networks from graph co-occurrence edges
        self._init_trust_networks(agents, graph)

        return agents

    def create_from_entity(
        self,
        entity: Entity,
        graph: KnowledgeGraph,
    ) -> AgentPersona:
        """Create a single AgentPersona from a knowledge graph entity."""
        # Determine role — promote high-mention entities
        base_role = ENTITY_ROLE_MAP.get(entity.entity_type, AgentRole.INDIVIDUAL)
        if entity.mention_count >= MEDIA_THRESHOLD:
            role = AgentRole.MEDIA
        elif entity.mention_count >= INFLUENCER_THRESHOLD:
            role = AgentRole.INFLUENCER
        else:
            role = base_role

        # Stance from observed sentiment
        stance = _stance_from_sentiment(entity.avg_sentiment)

        # Influence from graph statistics
        influence = _influence_from_mentions(
            entity.mention_count,
            entity.cross_platform_count,
        )

        # Build behavioral fingerprint
        fingerprint = BehavioralFingerprint(
            avg_posts_per_day=ROLE_ACTIVITY[role] * 10,
            avg_response_time_minutes=self._rng.uniform(5, 120),
            active_hours=list(range(8, 23)),
            sentiment_distribution={
                "positive": max(0.0, entity.avg_sentiment),
                "neutral": 1.0 - abs(entity.avg_sentiment),
                "negative": max(0.0, -entity.avg_sentiment),
            },
            preferred_platforms=list(entity.platforms_seen),
            influence_radius=influence,
            echo_chamber_score=self._rng.uniform(0.3, 0.8),
            persuadability=self._rng.uniform(0.2, 0.7),
            data_source="graph_entity",
            last_calibrated=datetime.now(),
        )

        return AgentPersona(
            agent_id=self._new_id(),
            name=entity.name,
            role=role,
            entity_type=entity.entity_type.value,
            activity_level=ROLE_ACTIVITY[role],
            stance=stance,
            sentiment_bias=entity.avg_sentiment,
            influence_weight=influence,
            fingerprint=fingerprint,
        )

    def create_synthetic(
        self,
        role: AgentRole = AgentRole.INDIVIDUAL,
        stance: Stance = Stance.NEUTRAL,
        name: Optional[str] = None,
        sentiment_bias: float = 0.0,
    ) -> AgentPersona:
        """Create a synthetic agent with given parameters."""
        name = name or f"Agent_{self._new_id()}"
        influence = ROLE_INFLUENCE[role]

        fingerprint = BehavioralFingerprint(
            avg_posts_per_day=ROLE_ACTIVITY[role] * 10,
            avg_response_time_minutes=self._rng.uniform(10, 60),
            active_hours=list(range(9, 22)),
            sentiment_distribution={"positive": 0.33, "neutral": 0.34, "negative": 0.33},
            preferred_platforms=["twitter", "reddit"],
            influence_radius=influence,
            echo_chamber_score=self._rng.uniform(0.2, 0.6),
            persuadability=self._rng.uniform(0.3, 0.7),
            data_source="synthetic",
        )

        return AgentPersona(
            agent_id=self._new_id(),
            name=name,
            role=role,
            entity_type=role.value,
            activity_level=ROLE_ACTIVITY[role],
            stance=stance,
            sentiment_bias=sentiment_bias,
            influence_weight=influence,
            fingerprint=fingerprint,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_bots(
        self,
        count: int,
        sentiment_bias: float = 0.0,
    ) -> List[AgentPersona]:
        """
        Create synthetic bot agents.
        Bots are split: half amplifiers (positive bias), half disruptors (negative).
        """
        bots = []
        for i in range(count):
            bias = 0.6 if i % 2 == 0 else -0.6
            stance = Stance.SUPPORTIVE if bias > 0 else Stance.OPPOSING
            bot = self.create_synthetic(
                role=AgentRole.BOT,
                stance=stance,
                name=f"Bot_{self._new_id()}",
                sentiment_bias=bias + sentiment_bias,
            )
            bots.append(bot)
        return bots

    def _init_trust_networks(
        self,
        agents: List[AgentPersona],
        graph: KnowledgeGraph,
    ) -> None:
        """
        Initialize agent trust networks from graph co-occurrence edges.
        Agents that co-occur in signals start with elevated trust.
        """
        agent_by_name: Dict[str, AgentPersona] = {
            a.name.lower(): a for a in agents
        }

        for agent in agents:
            neighbors = graph.get_entity_neighbors(
                graph._entity_by_name.get(agent.name.lower(), "")
            )
            for neighbor_entity, edge in neighbors:
                neighbor_agent = agent_by_name.get(neighbor_entity.name.lower())
                if neighbor_agent and neighbor_agent.agent_id != agent.agent_id:
                    # Co-occurrence weight → initial trust (capped at 0.8)
                    trust = min(0.8, 0.4 + edge.weight * 0.05)
                    agent.trust_network[neighbor_agent.agent_id] = trust
