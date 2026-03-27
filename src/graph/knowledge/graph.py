"""
Knowledge Graph — connects signals, entities, topics, and narratives.
Owner: Claude

This is the bridge between raw ingestion data and the simulation layer.
Entities are extracted from signals, linked by co-occurrence and sentiment,
and narratives are tracked as evolving subgraphs.

Based on MiroFish's Zep Cloud GraphRAG concept but implemented as a
lightweight in-memory graph first (swap to Zep/Neo4j when we scale).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from enum import Enum
from collections import defaultdict

from ...shared.types import ScoredSignal, Platform


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    PRODUCT = "product"
    LOCATION = "location"
    EVENT = "event"
    ASSET = "asset"  # crypto, stocks, etc.


class EdgeType(str, Enum):
    MENTIONS = "mentions"          # signal mentions entity
    CO_OCCURS = "co_occurs"        # two entities appear together
    SUPPORTS = "supports"          # sentiment: entity supports topic
    OPPOSES = "opposes"            # sentiment: entity opposes topic
    CAUSES = "causes"              # causal link
    PART_OF = "part_of"            # entity is part of a narrative


@dataclass
class Entity:
    """A node in the knowledge graph."""
    entity_id: str
    name: str
    entity_type: EntityType
    aliases: Set[str] = field(default_factory=set)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    mention_count: int = 0
    platforms_seen: Set[str] = field(default_factory=set)
    avg_sentiment: float = 0.0
    metadata: Dict = field(default_factory=dict)

    @property
    def cross_platform_count(self) -> int:
        return len(self.platforms_seen)


@dataclass
class Edge:
    """A relationship between two entities."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    signal_ids: List[str] = field(default_factory=list)


@dataclass
class NarrativeCluster:
    """A group of related entities forming a narrative."""
    cluster_id: str
    topic: str
    entity_ids: Set[str] = field(default_factory=set)
    signal_count: int = 0
    avg_sentiment: float = 0.0
    velocity: float = 0.0  # how fast this narrative is growing
    platforms: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class KnowledgeGraph:
    """
    In-memory knowledge graph connecting signals → entities → narratives.

    Pipeline:
    1. Ingest scored signals
    2. Extract entities from signal content
    3. Create edges between co-occurring entities
    4. Cluster related entities into narratives
    5. Track narrative evolution over time
    6. Export subgraphs for simulation seeding
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._edges: Dict[str, Edge] = {}  # "source:target:type" -> Edge
        self._narratives: Dict[str, NarrativeCluster] = {}

        # Indexes for fast lookup
        self._entity_by_name: Dict[str, str] = {}  # lowercase name -> entity_id
        self._edges_from: Dict[str, List[str]] = defaultdict(list)  # entity_id -> edge keys
        self._edges_to: Dict[str, List[str]] = defaultdict(list)

    def ingest_signals(
        self,
        scored_signals: List[ScoredSignal],
        query: str,
    ) -> Dict[str, int]:
        """
        Process scored signals into graph entities and edges.

        Returns counts: {"entities_created": N, "edges_created": M, ...}
        """
        stats = {"entities_created": 0, "entities_updated": 0,
                 "edges_created": 0, "edges_updated": 0}

        for scored in scored_signals:
            signal = scored.signal
            entities = self._extract_entities(signal.content)

            # Upsert each entity
            entity_ids = []
            for name, etype in entities:
                eid = self._upsert_entity(name, etype, signal.platform.value)
                entity_ids.append(eid)
                if eid not in self._entities or self._entities[eid].mention_count == 1:
                    stats["entities_created"] += 1
                else:
                    stats["entities_updated"] += 1

            # Create co-occurrence edges between all pairs
            for i, eid_a in enumerate(entity_ids):
                for eid_b in entity_ids[i + 1:]:
                    created = self._upsert_edge(eid_a, eid_b, EdgeType.CO_OCCURS)
                    if created:
                        stats["edges_created"] += 1
                    else:
                        stats["edges_updated"] += 1

            # Link entities to the query topic
            topic_eid = self._upsert_entity(query, EntityType.TOPIC, signal.platform.value)
            for eid in entity_ids:
                if eid != topic_eid:
                    self._upsert_edge(eid, topic_eid, EdgeType.MENTIONS)

        return stats

    def get_narrative_subgraph(
        self,
        topic: str,
        max_depth: int = 2,
    ) -> Dict:
        """
        Extract a subgraph around a topic for simulation seeding.

        Returns:
            {
                "entities": [Entity, ...],
                "edges": [Edge, ...],
                "stats": {"total_entities": N, "total_edges": M, ...}
            }
        """
        topic_lower = topic.lower()
        root_id = self._entity_by_name.get(topic_lower)
        if not root_id:
            return {"entities": [], "edges": [], "stats": {}}

        # BFS to collect connected entities up to max_depth
        visited: Set[str] = set()
        frontier = {root_id}
        all_entities: List[Entity] = []
        all_edges: List[Edge] = []

        for _ in range(max_depth):
            next_frontier: Set[str] = set()
            for eid in frontier:
                if eid in visited:
                    continue
                visited.add(eid)
                entity = self._entities.get(eid)
                if entity:
                    all_entities.append(entity)

                # Collect edges from this entity
                for edge_key in self._edges_from.get(eid, []):
                    edge = self._edges.get(edge_key)
                    if edge:
                        all_edges.append(edge)
                        if edge.target_id not in visited:
                            next_frontier.add(edge.target_id)

                for edge_key in self._edges_to.get(eid, []):
                    edge = self._edges.get(edge_key)
                    if edge:
                        all_edges.append(edge)
                        if edge.source_id not in visited:
                            next_frontier.add(edge.source_id)

            frontier = next_frontier

        return {
            "entities": all_entities,
            "edges": all_edges,
            "stats": {
                "total_entities": len(all_entities),
                "total_edges": len(all_edges),
                "platforms": len(set().union(*(e.platforms_seen for e in all_entities)) if all_entities else set()),
            },
        }

    def get_top_entities(self, limit: int = 20) -> List[Entity]:
        """Get most-mentioned entities."""
        return sorted(
            self._entities.values(),
            key=lambda e: e.mention_count,
            reverse=True,
        )[:limit]

    def get_entity_neighbors(self, entity_id: str) -> List[Tuple[Entity, Edge]]:
        """Get all entities connected to a given entity."""
        neighbors = []
        for edge_key in self._edges_from.get(entity_id, []):
            edge = self._edges.get(edge_key)
            if edge:
                target = self._entities.get(edge.target_id)
                if target:
                    neighbors.append((target, edge))

        for edge_key in self._edges_to.get(entity_id, []):
            edge = self._edges.get(edge_key)
            if edge:
                source = self._entities.get(edge.source_id)
                if source:
                    neighbors.append((source, edge))

        return neighbors

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def _extract_entities(self, content: str) -> List[Tuple[str, EntityType]]:
        """
        Extract entities from text content.

        Current: Heuristic extraction (capitalized phrases, known patterns).
        Future: spaCy NER or LLM extraction.
        """
        entities = []
        words = content.split()

        # Extract capitalized multi-word phrases (likely proper nouns)
        i = 0
        while i < len(words):
            word = words[i]
            # Skip very short or non-capitalized words
            if len(word) < 2 or not word[0].isupper():
                i += 1
                continue

            # Collect consecutive capitalized words
            phrase_words = [word]
            j = i + 1
            while j < len(words) and words[j][0:1].isupper() and len(words[j]) > 1:
                phrase_words.append(words[j])
                j += 1

            phrase = " ".join(phrase_words)
            # Skip common sentence starters and single-char words
            skip = {"The", "This", "That", "These", "Those", "When", "Where",
                    "What", "Which", "Who", "How", "Why", "But", "And", "For",
                    "Not", "With", "From", "Into", "About", "After", "Before"}
            if phrase not in skip and len(phrase) > 2:
                etype = self._classify_entity(phrase)
                entities.append((phrase, etype))

            i = j if j > i + 1 else i + 1

        # Extract $TICKER patterns
        import re
        tickers = re.findall(r'\$([A-Z]{1,5})\b', content)
        for ticker in tickers:
            entities.append((f"${ticker}", EntityType.ASSET))

        return entities

    def _classify_entity(self, phrase: str) -> EntityType:
        """Classify an entity type by heuristic."""
        lower = phrase.lower()

        # Asset patterns
        if phrase.startswith("$") or lower in {"bitcoin", "ethereum", "btc", "eth", "sol"}:
            return EntityType.ASSET

        # Known org patterns
        org_hints = {"inc", "corp", "ltd", "llc", "co", "foundation", "institute",
                     "commission", "department", "ministry", "agency", "bank"}
        if any(h in lower.split() for h in org_hints):
            return EntityType.ORGANIZATION

        # Location hints
        loc_hints = {"city", "state", "country", "island", "mountain", "river"}
        if any(h in lower.split() for h in loc_hints):
            return EntityType.LOCATION

        # Default to topic
        return EntityType.TOPIC

    def _upsert_entity(
        self, name: str, entity_type: EntityType, platform: str
    ) -> str:
        """Create or update an entity. Returns entity_id."""
        name_lower = name.lower()
        existing_id = self._entity_by_name.get(name_lower)

        if existing_id and existing_id in self._entities:
            entity = self._entities[existing_id]
            entity.mention_count += 1
            entity.last_seen = datetime.now()
            entity.platforms_seen.add(platform)
            return existing_id

        # Create new
        eid = f"e_{len(self._entities)}"
        entity = Entity(
            entity_id=eid,
            name=name,
            entity_type=entity_type,
            platforms_seen={platform},
            mention_count=1,
        )
        self._entities[eid] = entity
        self._entity_by_name[name_lower] = eid
        return eid

    def _upsert_edge(
        self, source_id: str, target_id: str, edge_type: EdgeType
    ) -> bool:
        """Create or update an edge. Returns True if newly created."""
        key = f"{source_id}:{target_id}:{edge_type.value}"

        if key in self._edges:
            edge = self._edges[key]
            edge.weight += 1.0
            edge.last_seen = datetime.now()
            return False

        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
        )
        self._edges[key] = edge
        self._edges_from[source_id].append(key)
        self._edges_to[target_id].append(key)
        return True
