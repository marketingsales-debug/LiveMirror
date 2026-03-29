# Research Audit: Layer 4 - Time-Series Forecasting
**Status:** Numerical Intelligence for Update 2.9 (The "Prediction" Pillar)  
**Selected Tools:** Chronos, Merlion, AutoGluon

---

## 🧐 Conceptual Overview
Move from "Qualitative Analysis" (Narratives) to "Quantitative Forecasting" (Numbers). This layer maps the intensity of social contagion to actual market moves (Price, Volume, Volatility) using state-of-the-art time-series models.

## 🚀 Key Technical Implementation Path

### 1. Zero-Shot Trend Projection (Chronos)
*   **The Logic:** An LLM-based architecture for time-series that treats numerical sequences as "tokens."
*   **Application:** Projects the "Narrative Tipping Point." It answers: "Given this 5-minute surge in Reddit hype, where will the price be in 60 minutes?"

### 2. Anomaly & Fraud Detection (Merlion)
*   **The Logic:** Salesforce's unified framework for anomaly detection in multi-variate time series.
*   **Application:** Identifies "Fake Hype." It flags instances where social sentiment is surging but actual on-chain/market volume is stagnant, a primary indicator of bot-driven manipulation.

### 3. Automated Ensemble Grading (AutoGluon)
*   **The Logic:** An AutoML framework that automatically trains and stacks the best performing models for tabular data.
*   **Application:** The "Master Aggregator." It takes the outputs of the Fusion Engine (86%), Reasoning Engine (94%), and Chronos (Forecasting) and finds the optimal mathematical weighting to maximize final accuracy.

## 🤝 Strategic Integration for Update 2.9

1.  **Numerical Forecasting Pipeline:** New module `src/prediction/numerical/` using Chronos.
2.  **Anomaly Monitor:** Integration of Merlion into the **Verification Step** of the agent board.
3.  **Final Consensus Score:** Deployment of AutoGluon as the top-level output generator.

---
**Decision:** High-impact for financial utility. Phase 15 moves LiveMirror from "Social Analysis" to "Financial Forecasting."
