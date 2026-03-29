# LiveMirror: Streamlined v2.0 Execution Plan
**Version:** 2.1 (Sane & Sprint-Based)  
**Status:** Sprint 1 Initialization  
**Baseline:** 86% Accuracy | **Target:** 94% (Verified via BacktestHarness)

---

## 📅 Sprint 1: The Foundation (Weeks 1-2)
**Goal:** Build a stateful, reliable spine that does not hallucinate.

*   **[ ] Phase 1: LangGraph Transition**
    *   Replace `agent_logic.py` with `src/orchestrator/graph.py`.
    *   Implement state persistence and error recovery nodes.
*   **[ ] Phase 2: Hallucination Guard (The Trust Layer)**
    *   Strict Pydantic schema enforcement for all LLM outputs.
    *   Source Citation Engine: Every claim must map to a signal ID.
    *   Locked temperature (0.0) for deterministic reasoning.
*   **[ ] Phase 3: Persistent Memory (Mem0)**
    *   Integrate Mem0 to track agent "lessons learned" across sessions.

## 📅 Sprint 2: The Intelligence (Weeks 3-4)
**Goal:** Shift from pattern-matching to deep logical reasoning.

*   **[ ] Phase 4: RARE Reasoning Architecture**
    *   Implement "Open-Book" distillation. 
    *   Decouple Signal Knowledge (RAG) from Narrative Logic (Transformer).
*   **[ ] Phase 5: RouteLLM (Cost Efficiency)**
    *   Deploy router to send simple tasks to local models, saving budget for RARE reasoning.
*   **[ ] Phase 6: Multi-Agent Research Board**
    *   Deploy specialized nodes: Researcher (RA), Engineer (EA), and Analyst.

## 📅 Sprint 3: Data & Verification (Weeks 5-6)
**Goal:** Scale the data quality and prove the 94% accuracy.

*   **[ ] Phase 7: Scientific Verification (PaperBench)**
    *   Implement Golden Rubrics for all core components.
    *   Deploy a "Judge Agent" to audit board proposals.
*   **[ ] Phase 8: Relational Memory (Qdrant + LightRAG)**
    *   Upgrade from local storage to high-velocity vector and graph retrieval.
*   **[ ] Phase 9: Delta Signal Analysis**
    *   Implement "Emotional Acceleration" metrics to predict tipping points.

---

## 🛡️ The "Mini-Pilot" Gate (Standard Operating Procedure)
No code is merged into `main` without passing the following:
1.  **Syntax Check**: Does it run?
2.  **Logic Check**: Does it pass the specific unit test?
3.  **Regression Check**: Does the overall accuracy stay >= current baseline?

---

## 📊 Concrete Target Definitions
*   **94% Accuracy**: Success rate in predicting the **Direction** (Bullish/Bearish) of a narrative tipping point 1 hour in advance, measured against the ICML historical dataset.
*   **45ms Latency**: End-to-end processing time for a single multimodal signal cluster.
