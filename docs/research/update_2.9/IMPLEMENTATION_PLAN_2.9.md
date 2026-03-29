# Implementation Plan: Update 2.9 (The Autonomous Scientist)

**Objective:** Move LiveMirror from "Static Code" to "Self-Evolving Intelligence" by adopting the Karpathy `autoresearch` protocol, `anarchitectural` interpolation, EvoScientist Multi-Agent logic, Frontier Algorithmic stabilizers, and Edge-Vision.

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
*   **Delta Signal Analysis:** Implement `emotional_delta` to track narrative acceleration.
*   **Elastic Caching:** Optimize KV-caches in the Sentiment Encoder to hit the "7x Speed" target.
*   **Reward-Based Verification (HERO):** Upgrade the Board's self-review logic to score code quality.

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
*   **Local Vision Encoder:** Use Moondream 0.5B to extract visual sentiment and body language cues at $0 cost.
*   **Agent Sight:** Give the **SelfMirror** board the ability to "see" screenshots of the dashboard to autonomously debug frontend issues.

## 📅 Roadmap for Implementation
1.  **Week 1:** Scaffold Sandbox, `EVOLUTIONARY_MEMORY.json`, and `src/skills/`.
2.  **Week 2:** Implement handover logic, Delta metrics, and Moondream vision encoder.
3.  **Week 3:** Deploy **Agent Router** and perform first "Self-Evolved Calibration" with Test-Time Reasoning.

---
**Success Criteria:** The system autonomously increases its own accuracy by >3%, reduces operational costs by 50%, and performs real-time multimodal analysis (Text+Audio+Video) on consumer-grade hardware.
