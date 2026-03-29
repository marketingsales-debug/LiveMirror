# Research Audit: LangGraph & Crawl4AI
**Status:** Core Engine Pivot for Update 2.9 (The "Agentic OS" Pillar)  
**Selected Tools:** LangGraph (LangChain), Crawl4AI

---

## 🧐 Conceptual Overview
Transition from a custom iterative loop to a **State-Machine Based Orchestrator** using LangGraph. Combine this with **Crawl4AI** for high-fidelity, LLM-optimized web signal extraction.

## 🚀 Key Technical Implementation Path

### 1. LangGraph State Machine
*   **The Logic:** Models agent workflows as a directed acyclic graph (DAG) or cyclic graph with persistent state and "Human-in-the-loop" breakpoints.
*   **Application:** Powers the **Multi-Agent Research Board**. Enables complex handoffs between the Researcher, Engineer, and Analyst agents, with native rollback support and state recovery.

### 2. Crawl4AI (LLM-Optimized Scraping)
*   **The Logic:** A high-performance web crawler designed specifically to return clean, structured Markdown for AI agents.
*   **Application:** The primary "Eyes" of the system. Replaces generic scraping with a robust engine that can handle JavaScript-heavy sites and provide high-signal data for the Fusion Engine.

## 🤝 Strategic Integration for Update 2.9

1.  **LangGraph Orchestrator:** New core module `src/orchestrator/graph.py` replacing `agent_logic.py`.
2.  **Crawl4AI Modality:** Integration of Crawl4AI into the `src/ingestion/web/` layer.
3.  **State Persistence:** Use LangGraph's memory savers to store research trajectories in **Mem0**.

---
**Decision:** 10/10 Move. This pivot provides the industrial-grade stability needed for a self-evolving system.
