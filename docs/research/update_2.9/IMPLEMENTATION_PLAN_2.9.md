# LiveMirror: Lean v2.0 Execution Plan
**Version:** 2.2 (The Lean Stack)  
**Baseline:** 86% Accuracy | **Target:** 94% (Verified via BacktestHarness)

---

## 🏗️ The Lean Architecture (4 Core Dependencies)
1.  **LangGraph** (Orchestration OS)
2.  **Qdrant** (Vector Memory)
3.  **vLLM** (Local Inference Serving)
4.  **Crawl4AI** (High-Fidelity Scraping)

---

## 📅 Sprint 1: Foundation & Reliability (Weeks 1-2)
**Goal:** Build the stateful spine and eliminate hallucinations.

*   **[ ] Module: `src/orchestrator/` (LangGraph Transition)**
    *   Implement the multi-agent state machine.
    *   Nodes: Researcher, Coder, Analyst, EMA.
*   **[ ] Module: `src/guards/` (Hallucination Guard)**
    *   Strict Pydantic schema validation for all LLM outputs.
    *   Citation Engine: Logic to verify claims against Crawl4AI signal IDs.
*   **[ ] Module: `src/memory/` (Simplified Memory Tier)**
    *   **Vector:** Qdrant integration.
    *   **Session:** SQLite store for agent interaction history (extracted from Mem0).
    *   **Graph:** LLM-based Triple Extraction (extracted from LightRAG).

## 📅 Sprint 2: Intelligence & Routing (Weeks 3-4)
**Goal:** Move from "Guessing" to "Reasoning" while optimizing costs.

*   **[ ] Module: `src/reasoning/` (Logical RARE Architecture)**
    *   Open-book prompting (Force RAG retrieval).
    *   Shifted-Thinking Window (extracted from Z1).
    *   Rejection-sampled distillation for training student models.
*   **[ ] Module: `src/routing/` (Economic Routing)**
    *   Implement a simple signal-complexity scorer.
    *   Route easy signals to local models, hard signals to GPT-5.1.
*   **[ ] Module: `src/observability/` (The Flight Recorder)**
    *   Structured JSON logging of every prediction cycle.
    *   Cost and latency metrics tracking (extracted from AgentOps).

## 📅 Sprint 3: Simulation & Skills (Weeks 5-6)
**Goal:** Scale social behavior and verify the 94% accuracy.

*   **[ ] Module: `src/simulation/` (Generative Behavior)**
    *   Add Memory Stream and Reflection to agents (extracted from Stanford).
    *   Implement susceptibility scores for contagion modeling.
*   **[ ] Module: `src/skills/` (Expertise Packs)**
    *   Elo-based Signal Tournament logic.
    *   Modality Ablation workflow.
*   **[ ] Final Calibration:**
    *   Run PaperBench-style reproduction tests to prove 94% accuracy.

---

## 🛡️ The "Mini-Pilot" SOP
Every commit must pass:
1.  **Syntax**: `python -m compileall .`
2.  **Logic**: Pass the specific `pytest` for the new module.
3.  **Regression**: Backtest accuracy must not drop below 86%.
