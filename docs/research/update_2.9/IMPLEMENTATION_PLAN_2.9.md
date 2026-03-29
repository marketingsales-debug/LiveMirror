# Implementation Plan: Update 2.9 (The Autonomous Scientist)

**Objective:** Move LiveMirror from "Static Code" to "Self-Evolving Intelligence" by adopting the Karpathy `autoresearch` protocol and `anarchitectural` interpolation.

---

## 🏗️ Phase 1: The Research Sandbox (`src/research_sandbox/`)
Establish a restricted environment where the **SelfMirror** agent has full "Self-Modification" permissions.
*   **Action:** Create `src/research_sandbox/train_fusion.py`.
*   **Action:** Create `src/research_sandbox/results.tsv` to track cross-generational progress.
*   **Goal:** Allow the agent to rewrite fusion logic without breaking the production `src/fusion/` path.

## 🧪 Phase 2: The Evaluation Engine
Connect the sandbox to our existing `BacktestHarness`.
*   **Protocol:** 
    1.  Agent modifies `train_fusion.py`.
    2.  Agent runs `python train_fusion.py --limit-time 300` (The 5-minute Karpathy constraint).
    3.  `BacktestHarness` evaluates the resulting weights against historical data.
    4.  The system records Accuracy, Latency, and BPB.

## 🧠 Phase 3: The Research Protocol (`research_protocol.md`)
Program the "Agent's Brain" using the Markdown-as-Code pattern.
*   **Instruction Set:**
    - "Propose a hypothesis for why current sentiment weighting is failing on crypto-slang."
    - "Modify the Attention Head count in the Sandbox."
    - "If results.tsv shows improvement, propose a Merge Request to the production fusion engine."

## 🛡️ Phase 4: The Stability Layer (Weight Interpolation)
Use the `anarchitectural-search` logic to prevent "Catastrophic Forgetting."
*   **Logic:** When merging a self-discovered model into production, do not replace the weights.
*   **Implementation:** Use **Spherical Linear Interpolation (Slerp)** or **Weight Blending** to slowly transition from the old model to the agent-optimized model.

## 📅 Roadmap for Implementation
1.  **Week 1:** Scaffold the `src/research_sandbox/` and basic 5-minute runner.
2.  **Week 2:** Draft the `research_protocol.md` and perform the first "Autonomous Calibration" run.
3.  **Week 3:** Implement the Weight Interpolation merge logic to safely push AI-discovered improvements to the `main` branch.

---
**Success Criteria:** The system successfully autonomously increases its own accuracy by >2% without human code changes.
