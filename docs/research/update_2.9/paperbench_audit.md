# Research Audit: OpenAI PaperBench
**Status:** Verification Framework for Update 2.9 (The "Validation" Pillar)  
**Reference:** [openai/frontier-evals/paperbench](https://github.com/openai/frontier-evals/tree/main/project/paperbench)

---

## 🧐 Conceptual Overview
PaperBench evaluates the ability of AI agents to perform end-to-end autonomous research replication. It requires agents to rebuild complex ML projects from scratch based solely on research papers, without access to original source code.

## 🚀 Key Technical Insights from Implementation

### 1. Code-Free Replication Task
*   **The Logic:** Forces the agent to internalize mathematical and architectural logic from text/Markdown rather than copying code.
*   **Application:** Use this to expand LiveMirror's capabilities. When a new research paper on "Financial Signal Fusion" is released, the **SelfMirror Board** is tasked with autonomously implementing the paper's core algorithm into the `src/fusion/` pipeline.

### 2. Hierarchical Grading Rubrics (SimpleJudge)
*   **The Logic:** Break down complex research goals into thousands of small, verifiable tasks co-developed with domain experts.
*   **Application:** Create a `docs/rubrics/` system for LiveMirror. Every autonomous refactor or calibration attempt by the agent board is graded against a specific quality/logic rubric before it is allowed to merge.

### 3. Agent Rollout & Reproduction Pipeline
*   **The Logic:** A three-stage pipeline (Work -> Reproduce -> Grade) that ensures behavioral correctness.
*   **Application:** Formalize our **Verify** step. Instead of just running `pytest`, the system will perform a full "Reproduction Run" in the Research Sandbox to prove that the new logic actually hits the accuracy targets.

## 🤝 Strategic Implementation for Update 2.9

1.  **Golden Rubric System:** Define strict logic-check rubrics in `docs/rubrics/v2.0_accuracy.json`.
2.  **Autonomous Paper Implementation:** Add a skill to the `src/skills/` library that allows the agent to ingest a Markdown-formatted research paper and propose a new modality encoder.
3.  **LLM-Judge Verification:** Implement a "Reviewer" agent on the board that uses PaperBench-style grading logic.

---
**Decision:** Essential for maintaining "Human-Level" engineering quality. Phase 12 will focus on making the agent board self-grading.
