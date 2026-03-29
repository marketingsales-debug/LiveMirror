# Implementation Plan: Update 2.9 (The Autonomous Scientist)

**Objective:** Move LiveMirror from "Static Code" to "Self-Evolving Intelligence" by adopting the Karpathy `autoresearch` protocol, `anarchitectural` interpolation, and EvoScientist Multi-Agent logic.

---

## 🏗️ Phase 1: The Research Sandbox (`src/research_sandbox/`)
Establish a restricted environment where the **SelfMirror** agent board has full "Self-Modification" permissions.
*   **Action:** Create `src/research_sandbox/train_fusion.py`.
*   **Action:** Create `src/research_sandbox/results.tsv` to track cross-generational progress.

## 🧪 Phase 2: The Multi-Agent Research Board
Transition from a single agent to a specialized team based on **EvoScientist** roles:
1.  **Researcher (RA):** Proposes hypotheses for weight adjustments (e.g., "Increasing Audio-Reliability-Weight will catch more CEO deception during earnings calls").
2.  **Engineer (EA):** Modifies the `train_fusion.py` code in the Sandbox.
3.  **Analyst:** Runs the 5-minute Karpathy-style training and evaluates via `BacktestHarness`.
4.  **Evolution Manager (EMA):** Distills the interaction into `EVOLUTIONARY_MEMORY.json`.

## 🧠 Phase 3: Persistent Evolutionary Memory (`EVOLUTIONARY_MEMORY.json`)
Program the "Agent's Wisdom" to survive across sessions.
*   **Ideation Memory:** "Hypothesis #42 (Text-Bias reduction) failed due to high noise in Bluesky data."
*   **Experimentation Memory:** "Normalization Function 'v3_clipping' improved accuracy by 1.2% on volatile signals."

## 🛡️ Phase 4: The Stability Layer (Weight Interpolation)
Use the `anarchitectural-search` logic to safely merge self-discovered improvements.
*   **Logic:** Use **Spherical Linear Interpolation (Slerp)** to blend the "Human-Built v1.0" model with the "AI-Optimized v2.0" model to prevent regression.

## 📅 Roadmap for Implementation
1.  **Week 1:** Scaffold the Research Sandbox and `EVOLUTIONARY_MEMORY.json`.
2.  **Week 2:** Implement the Multi-Agent handover logic (RA -> EA -> Analyst).
3.  **Week 3:** Perform the first "Self-Evolved Calibration" and safe Slerp merge into `main`.

---
**Success Criteria:** The system successfully autonomously discovers a new "Research Strategy" that results in a verifiable accuracy boost stored in its persistent memory.
