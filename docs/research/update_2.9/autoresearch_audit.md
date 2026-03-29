# Research Audit: Karpathy Autoresearch
**Status:** High Priority for Update 2.9 (The "Autonomous Intelligence" Pillar)  
**Reference Repo:** [karpathy/autoresearch](https://github.com/karpathy/autoresearch)

---

## 🧐 Conceptual Overview
This project shifts the paradigm from AI-as-a-coder to **AI-as-a-Scientist**. It creates a closed-loop system where an agent proposes hypotheses, modifies training code, runs experiments with a fixed time-budget, and iterates based on standardized metrics.

## 🚀 Unique "Super Interesting" Features

### 1. The 5-Minute Wall-Clock Constraint
*   **The Logic:** Every experiment is hard-capped at 5 minutes of execution.
*   **The Result:** The agent is forced to find the "Goldilocks" zone of efficiency. It cannot just build a "bigger" model; it must build a *smarter* one that learns the most within that specific hardware/time window.

### 2. Bits-Per-Byte (BPB) Standard
*   **The Logic:** Using a vocab-independent metric instead of raw Loss.
*   **The Result:** The agent can experiment with totally different tokenization and architecture strategies without "gaming" the loss function.

### 3. "Programming the Program"
*   **The Logic:** The agent's instructions are not code, but a Markdown "manual" (`program.md`).
*   **The Result:** Humans become "Research Managers" who define the protocol, while the AI performs the low-level scientific iteration.

## 🤝 Potential "Scientific" Applications for LiveMirror

### 1. Autonomous Fusion Calibration
*   Let **SelfMirror** iterate on the weighting between Sentiment, Intent, and Audio signals using the 5-minute constraint against our `BacktestHarness`.

### 2. Self-Evolving Scrapers
*   Allow the agent to rewrite scraper logic to maximize "Signals-Per-Second" efficiency within a fixed execution window.

### 3. Hyper-Architecture Search
*   Autonomous discovery of optimal Attention Head counts and Layer depths for the **LearnedCrossModalAttention** engine.

---
**Decision:** High-impact. This logic will form the backbone of the "Self-Evolution" phase of LiveMirror v2.0.
