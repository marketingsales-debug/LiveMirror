# Research Audit: Layer 3 - Long-Term Memory & RAG
**Status:** Memory Architecture for Update 2.9 (The "Brain" Pillar)  
**Selected Tools:** LlamaIndex, Qdrant, Mem0, LightRAG, Memgraph

---

## 🧐 Conceptual Overview
Move from "Stateless" processing to a multi-tiered memory system. This allows LiveMirror to remember historical market regimes, track agent evolution across sessions, and understand complex relational manipulation patterns.

## 🚀 Key Technical Implementation Path

### 1. High-Velocity Vector Backbone (Qdrant + LlamaIndex)
*   **The Logic:** Use Rust-based Qdrant for real-time signal embeddings and LlamaIndex for agentic orchestration.
*   **Application:** Provides the "Fact Base" for the RARE Reasoning engine. Enables <15ms retrieval of similar historical narratives.

### 2. Relational Narrative Intelligence (LightRAG)
*   **The Logic:** Extracts Knowledge Graphs from unstructured social signals to understand multi-hop relationships.
*   **Application:** Detects coordinated manipulation. Instead of looking at raw sentiment, the system sees the *network* of influencers and bots driving a narrative.

### 3. Cross-Session Evolutionary Memory (Mem0)
*   **The Logic:** A persistent memory layer that tracks agent learning and user preferences across separate sessions.
*   **Application:** Powers the **Evolutionary Memory** planned in Phase 3. Ensures the Agent Board "remembers" which research hypotheses failed weeks ago.

### 4. In-Memory Simulation Graph (Memgraph)
*   **The Logic:** An in-memory graph database for high-frequency relationship updates.
*   **Application:** Real-time tracking of contagion spread during 72-round simulation tournaments.

## 🤝 Strategic Integration for Update 2.9

1.  **Tiered Memory Pipeline:** New module `src/shared/memory/` orchestrating Qdrant and Mem0.
2.  **Relational Indexer:** Deployment of **LightRAG** in the ingestion pipeline.
3.  **Simulation State Store:** Integration of **Memgraph** for the Synthetic Agent Factory.

---
**Decision:** Essential for v2.0 scale. Phase 14 transforms the system from a "Live Mirror" into a "Living History" that learns from the past.
