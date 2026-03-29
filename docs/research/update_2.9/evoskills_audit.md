# Research Audit: EvoSkills
**Status:** Skill-Based Infrastructure for Update 2.9 (The "Modular Expertise" Pillar)  
**Reference:** [EvoSkills Repository](https://github.com/EvoScientist/EvoSkills)

---

## 🧐 Conceptual Overview
EvoSkills is a library of "installable knowledge packs" that extend AI agents with specific domain expertise. It moves away from generic prompting toward **Structured Workflows** and **Diagnostic Flows**.

## 🚀 Unique "Skill-Based" Features

### 1. Elo-Based Idea Tournament
*   **The Logic:** Agents generate multiple hypotheses/signals and make them "fight" in a tournament.
*   **The Result:** Only the most robust, high-impact ideas survive, ranked by a competitive Elo score.

### 2. Counterintuitive Rules (Anti-Bias)
*   **The Logic:** Encoded rules that steer the AI away from incremental thinking (e.g., "Write the rejection letter first").
*   **The Result:** Higher novelty and better anticipation of experimental failure.

### 3. Attempt Budgets & Ablation
*   **The Logic:** Hard caps on execution attempts to prevent "rabbit holes" and structured "ablation" (removing components to test their individual value).
*   **The Result:** Highly efficient research iteration and verified component impact.

## 🤝 Potential "Skill" Applications for LiveMirror

### 1. Signal Tournament Skill
*   Instead of processing every signal, run a tournament to identify the top 10 "Winning Signals" based on credibility, velocity, and cross-modal alignment.

### 2. The Ablation Workflow
*   Autonomously test the fusion engine by "turning off" specific modalities (Audio, Intent, etc.) to prove their contribution to the 94% accuracy target.

### 3. Modular Skill Architecture
*   Establish a `src/skills/` folder where specialized research behaviors can be plugged in without bloating the core `agent_logic.py`.

---
**Decision:** High-impact infrastructure change. This will make the SelfMirror agent modular and allow us to swap "Expertises" on the fly.
