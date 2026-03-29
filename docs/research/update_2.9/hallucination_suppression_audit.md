# Research Audit: Hallucination Suppression Protocol
**Status:** Foundational Requirement for Update 2.9 (The "Trust" Pillar)  
**Goal:** Eliminate "Probabilistic Guessing" and ensure 100% grounded predictions.

---

## 🧐 Conceptual Overview
LLMs are probability engines, not fact engines. To predict the future accurately, LiveMirror must treat the LLM as a **Logic Processor** while using external databases as the **Memory**.

## 🚀 Key Suppression Measures

### 1. RAG-Based Grounding (The "Open-Book" Rule)
*   **Protocol:** The agent is explicitly forbidden from using internal knowledge for market facts (e.g., "What is the current BTC price?").
*   **Enforcement:** The system prompt will include: *"If the required data is not in the retrieved context, you must trigger a SEARCH_WEB action or state 'Insufficient Data'."*

### 2. Multi-Agent Cross-Examination (LangGraph)
*   **Node A (Generator):** Proposes a prediction based on signals.
*   **Node B (Verifier/Judge):** Matches the prediction's logic against raw signal Markdown (from Crawl4AI).
*   **Action:** If Node B detects an unverified claim, the state returns to Node A for a "Rethink" (Z1-style).

### 3. Structured Logic (JSON Enforcement)
*   **The Logic:** Hallucinations thrive in free-form text.
*   **Application:** Every agent output must conform to a strict Pydantic schema. This forces the agent to categorize its logic into `observation`, `reasoning`, `evidence`, and `conclusion`.

### 4. Deterministic Sampling
*   **Enforcement:** Set `temperature=0` and `top_p=1` for all nodes in the LangGraph except the "Researcher Agent" (during ideation only).

## 🤝 Integration into Update 2.9 Implementation

1.  **Hallucination Guard Skill:** A new skill in `src/skills/` that performs "Span-Level Verification" (checking every sentence against the context).
2.  **Citation Engine:** Refactor the **Fusion Engine** to return `(Signal, Confidence, Source_URL)` tuples for every output.
3.  **Judge Node:** Implementation of the **PaperBench-style Judge** in the LangGraph orchestrator.

---
**Decision:** Non-negotiable for v2.0. Reliability is the difference between a "Gimmick" and an "Industrial Prediction Engine."
