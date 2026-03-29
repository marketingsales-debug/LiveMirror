# Implementation Plan: Update 2.9 (The Autonomous Scientist)

**Objective:** Move LiveMirror from "Static Code" to "Self-Evolving Intelligence" by adopting the Karpathy `autoresearch` protocol, `anarchitectural` interpolation, EvoScientist Multi-Agent logic, and Frontier Algorithmic stabilizers.

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
*   **Logic:** Use **Slerp** or weight blending to merge AI-optimized weights into the `main` branch without causing "Catastrophic Forgetting."

## 🛠️ Phase 5: Modular Skill Architecture (`src/skills/`)
Adopt the **EvoSkills** pattern to give the board specific "Expertise Packs."
*   **Signal Tournament Skill:** A workflow for ranking narrative signals by Elo score.
*   **Ablation Skill:** A workflow for identifying redundant modality components.

## ⚡ Phase 6: Algorithmic Stabilizers (Frontier Theory)
Integrate recent breakthroughs from dair-ai ML research (2025-2026).
*   **Delta Signal Analysis:** Implement `emotional_delta` to track the *acceleration* of narrative growth.
*   **Elastic Caching:** Optimize KV-caches in the Sentiment Encoder to hit the "7x Speed" target.
*   **Reward-Based Verification (HERO):** Upgrade the Board's self-review logic to score code quality, not just test results.

## 📅 Roadmap for Implementation
1.  **Week 1:** Scaffold Sandbox, `EVOLUTIONARY_MEMORY.json`, and `src/skills/`.
2.  **Week 2:** Implement RA -> EA -> Analyst handover and "Delta Sentiment" metrics.
3.  **Week 3:** Perform the first "Self-Evolved Calibration" with Elastic Caching and Slerp merge.

---
**Success Criteria:** The system autonomously increases its own accuracy by >3% and reduces latency to <15ms through self-discovered algorithmic optimizations.
