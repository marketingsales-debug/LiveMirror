# Research Audit: Layer 8 - AI Observability & Programmatic Optimization
**Status:** Evaluation Framework for Update 2.9 (The "Reliability" Pillar)  
**Selected Tools:** DSPy (Stanford), AgentOps, WandB, Ragas

---

## 🧐 Conceptual Overview
Move from "Vibe-based Prompting" to **Programmatic AI Engineering**. This layer ensures every LLM call is monitored for cost/latency, every reasoning loop is recorded, and every prompt is autonomously optimized for maximum accuracy.

## 🚀 Key Technical Implementation Path

### 1. Programmatic Prompt Optimization (DSPy)
*   **The Logic:** Replaces manual prompt engineering with "Signatures" and "Optimizers" that autonomously find the best instructions based on a few examples.
*   **Application:** Upgrade the **SelfMirror Board**. Instead of us writing the system prompt, DSPy will compile the optimal instructions for the Researcher and Coder agents to maximize their success rate in the Research Sandbox.

### 2. Agentic Flight Recorder (AgentOps)
*   **The Logic:** A specialized monitoring suite for autonomous agents that tracks tool usage, cost per session, and multi-step reasoning trajectories.
*   **Application:** Observability for the **Multi-Agent Board**. Provides a "Black Box" recorder for every research goal. If the Board gets stuck in a loop or makes a costly API mistake, AgentOps flags it instantly.

### 3. RAG Quality Metrics (Ragas)
*   **The Logic:** A framework that scores RAG pipelines on Faithfulness, Answer Relevance, and Context Precision.
*   **Application:** Validation for **Phase 14 (Memory)**. Ensures that the historical narratives retrieved from Qdrant/LightRAG are actually relevant to the current market signal, preventing "Garbage-In, Garbage-Out" reasoning.

### 4. Experiment Registry (Weights & Biases)
*   **The Logic:** The industry standard for tracking ML experiments, loss curves, and model versions.
*   **Application:** Tracking the **Autonomous Scientist** progress. Every 5-minute training run and every Slerp merge is logged to WandB, allowing us to visualize the Accuracy (86% -> 94%) and Latency improvements over the 12-week roadmap.

## 🤝 Strategic Integration for Update 2.9

1.  **Programmatic Agent Signatures:** Refactor `src/skills/` to use **DSPy** modules instead of raw string prompts.
2.  **Observability Middleware:** Integrate **AgentOps** and **Helicone** (for cost) into `backend/self_mirror/agent_logic.py`.
3.  **Validation Unit Tests:** Use **Ragas** inside the `BacktestHarness` to score the quality of retrieved signal context.

---
**Decision:** High-impact for v2.0 stability. Phase 18 ensures that as the system evolves autonomously, it remains cost-effective, transparent, and mathematically grounded.
