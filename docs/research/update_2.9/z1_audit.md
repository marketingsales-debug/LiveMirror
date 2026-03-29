# Research Audit: Z1 (Efficient Test-time Scaling with Code)
**Status:** Compute Efficiency for Update 2.9 (The "Inference Scaling" Pillar)  
**Reference:** [efficientscaling/Z1 Repository](https://github.com/efficientscaling/Z1)

---

## 🧐 Conceptual Overview
Z1 introduces a formal framework for **Test-time Scaling**, allowing LLMs to improve their reasoning by spending more compute (tokens) during inference. Its core innovation is the **Shifted Thinking Window**, which prevents models from getting stuck in circular reasoning loops by forcing a "synthesis" phase.

## 🚀 Key Technical Insights from Implementation

### 1. Shifted Thinking Window
*   **The Logic:** A two-stage inference process. Stage 1 generates a long reasoning/code trajectory. Stage 2 is triggered by a "Shift" prompt that forces the model to synthesize Stage 1 into a final answer.
*   **Application:** Use this to prevent **Prediction Drift** in LiveMirror. If the agent gets stuck debating a complex social signal, the Shift-Prompt forces a final, grounded prediction.

### 2. Code-Centric Reasoning
*   **The Logic:** Uses code as the primary medium for rigorous logic rather than natural language.
*   **Application:** Upgrade the **Fusion Engine** to verify probabilistic weights by generating and running "Micro-Backtests" on the fly during the "Thinking Stage."

### 3. Variable Inference Budget
*   **The Logic:** Performance scales linearly with the token budget allocated to the "Thinking Window."
*   **Application:** Implement **Dynamic Prediction Quality**. High-volatility signals receive a 4,000-token thinking budget (High Accuracy), while low-volatility signals use a 200-token budget (Low Latency/Cost).

## 🤝 Strategic Implementation for Update 2.9

1.  **Thinking Orchestrator:** New module `src/orchestrator/thinking.py` to manage the Z1-style two-stage inference.
2.  **Dynamic Compute Scheduler:** Logic to adjust the thinking window size based on signal volatility metrics.
3.  **Synthesis Trigger:** Implement the "Shifted Thinking" prompt logic in the agent's system instruction.

---
**Decision:** High priority for v2.0 flexibility. This allows LiveMirror to trade off speed vs. accuracy dynamically based on market conditions.
