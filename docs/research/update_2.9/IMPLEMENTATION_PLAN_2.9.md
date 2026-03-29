# Implementation Plan: Update 2.9 (The Autonomous Scientist)

**Objective:** Move LiveMirror from "Static Code" to "Self-Evolving Intelligence" by adopting the Karpathy `autoresearch` protocol, `anarchitectural` interpolation, EvoScientist Multi-Agent logic, Frontier Algorithmic stabilizers, Edge-Vision, RARE Reasoning, Z1 Inference Scaling, and PaperBench Verification.

---

## 🏗️ Phase 1: The Research Sandbox (`src/research_sandbox/`)
Establish a restricted environment where the **SelfMirror** agent board has full "Self-Modification" permissions.
*   **Action:** Create `src/research_sandbox/train_fusion.py`.
*   **Action:** Create `src/research_sandbox/results.tsv` to track cross-generational progress.

## 🧪 Phase 2: The Multi-Agent Research Board
Transition from a single agent to a specialized team based on **EvoScientist** roles:
1.  **Researcher (RA):** Proposes hypotheses for weight adjustments.
2.  **Engineer (EA):** Modifies code in the Sandbox.
3.  **Analyst:** Runs the 5-minute training and evaluates via `BacktestHarness`.
4.  **Evolution Manager (EMA):** Distills interaction into persistent memory.

## 🧠 Phase 3: Persistent Evolutionary Memory (`EVOLUTIONARY_MEMORY.json`)
Program the "Agent's Wisdom" to survive across sessions.
*   **Ideation Memory:** Tracks what hypotheses succeeded or failed.
*   **Experimentation Memory:** Stores reusable code-patterns for data normalization.

## 🛡️ Phase 4: The Stability Layer (Weight Interpolation)
Use the `anarchitectural-search` logic to safely merge self-discovered improvements.
*   **Logic:** Use **Slerp** or weight blending to merge AI-optimized weights into the `main` branch.

## 🛠️ Phase 5: Modular Skill Architecture (`src/skills/`)
Adopt the **EvoSkills** pattern to give the board specific "Expertise Packs."
*   **Signal Tournament Skill:** A workflow for ranking narrative signals by Elo score.
*   **Ablation Skill:** A workflow for identifying redundant modality components.

## ⚡ Phase 6: Algorithmic Stabilizers (Frontier Theory)
Integrate recent breakthroughs from dair-ai ML research (2025-2026).
*   **Delta Signal Analysis:** Implement `emotional_delta` to track narrative acceleration.
*   **Elastic Caching:** Optimize KV-caches in the Sentiment Encoder.
*   **Reward-Based Verification (HERO):** Upgrade the Board's self-review logic.

## 👥 Phase 7: High-Fidelity Social Simulation (SocioVerse)
Upgrade the behavioral realism of synthetic agents based on April 2025 research.
*   **Socio-Emotional Fingerprints:** Implement "Archetypes" (FOMO-Spreader, Skeptic, Whale) in `AgentFactory`.
*   **Test-Time Reasoning (M1):** Implement deep-reasoning buffers in the orchestrator.

## 📉 Phase 8: Operational Excellence (Cost & Performance Routing)
Optimize the system for production-scale economics and temporal awareness.
*   **Agent Router (RouteLLM):** Direct simple tasks to cheap local models.
*   **Temporal Vision Fusion:** Upgrade video analysis to use joint temporal representations.
*   **FP8 Attention (FlashAttention-3):** Implement asynchronous FP8 attention.

## 👁️ Phase 9: Edge-Vision Intelligence (Moondream)
Integrate local, ultra-efficient vision processing for real-time multimodal analysis.
*   **Local Vision Encoder:** Use Moondream 0.5B to extract visual sentiment at $0 cost.
*   **Agent Sight:** Enable board to "see" screenshots for autonomous UI debugging.

## 🧠 Phase 10: RARE Reasoning Architecture
Transform the system from pattern-matching to structured "Open-Book" reasoning.
*   **Knowledge-Reasoning Separation:** Decouple signal retrieval from analysis logic.
*   **Dynamic Thinking Buffer (Open Deep Search):** Implement test-time search scaling.
*   **Architectural Refactor Skill:** Enable Board to autonomously optimize codebase structure.

## ⏱️ Phase 11: Z1 Shifted-Thinking Engine
Implement efficient test-time scaling to trade off compute for accuracy dynamically.
*   **Thinking Orchestrator:** Manage two-stage inference (Trajectory + Synthesis).
*   **Variable Compute Scheduler:** Adjust Thinking Window based on signal volatility.

## ✅ Phase 12: Autonomous R&D Verification (PaperBench)
Establish "Human-Level" engineering standards for the agent board.
*   **Golden Rubric System:** Create `docs/rubrics/` to grade autonomous code changes against expert standards.
*   **Reproduction Pipeline:** Formalize the "Verify" step into a full-scale reproduction run in the Sandbox.
*   **Judge Agent:** Implement a specialized board role that uses SimpleJudge logic to approve or reject merges.

## 📅 Roadmap for Implementation
1.  **Week 1:** Scaffold Sandbox, `EVOLUTIONARY_MEMORY.json`, `src/skills/`, and Agent Router.
2.  **Week 2:** Implement handover logic, Delta metrics, and RARE Open-Book refactor.
3.  **Week 3:** Deploy Z1 Thinking, PaperBench Rubrics, and perform first "Self-Evolved" Slerp merge.

---
**Success Criteria:** The system autonomously increases accuracy to 94% with <45ms latency, 50% cost reduction, and human-verified engineering quality across all patches.
