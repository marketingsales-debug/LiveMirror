# Research Audit: Layer 5 - Ingestion & Orchestration
**Status:** Infrastructure for Update 2.9 (The "Plumbing" Pillar)  
**Selected Tools:** Redpanda, dlt, Dagster

---

## 🧐 Conceptual Overview
Move from "One-off Scripts" to a **Decoupled Event-Driven Architecture**. This ensures the system is resilient to API failures, scales to hundreds of concurrent signals, and provides professional-grade observability for the entire ML lifecycle.

## 🚀 Key Technical Implementation Path

### 1. High-Performance Event Bus (Redpanda)
*   **The Logic:** A C++ implementation of the Kafka protocol that provides ultra-low latency without the complexity of ZooKeeper.
*   **Application:** The "Heart" of the system. Scrapers push raw signals into Redpanda topics. The Fusion Engine consumes these topics in real-time. This prevents data loss during high-volatility events where signal velocity might spike.

### 2. Schema-Fluid Data Loading (dlt)
*   **The Logic:** A lightweight Python library that automates the extraction and loading of data from nested JSON (APIs) into structured stores.
*   **Application:** Standardization. It ensures that signals from diverse sources (GitHub, Reddit, Twitter) are normalized into a unified "Signal Schema" before hitting the Vector Store or Knowledge Graph.

### 3. Software-Defined Orchestration (Dagster)
*   **The Logic:** A modern orchestrator that focuses on "Data Assets" and their dependencies rather than just "Tasks."
*   **Application:** The "Brain's Manager." Dagster orchestrates the complex Update 2.9 lifecycle: Signal Ingestion -> Cross-Modal Fusion -> Multi-Agent Debate -> Backtesting -> Fine-Tuning. It provides full lineage and error-tracking for every prediction.

## 🤝 Strategic Integration for Update 2.9

1.  **Streaming Architecture:** New module `src/shared/streaming/` using Redpanda.
2.  **Pipeline Standardization:** Refactor `src/ingestion/` to use **dlt** for all 10 platform scrapers.
3.  **MLOps Dashboard:** Deployment of **Dagster** to manage the "Autonomous Scientist" loop (Phase 13).

---
**Decision:** Essential for production reliability. Phase 16 moves LiveMirror from a "Research Prototype" to a "Resilient Industrial Engine."
