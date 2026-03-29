# Research Audit: Layer 6 - Autonomous Operations & Web Intelligence
**Status:** Operational Agency for Update 2.9 (The "Action" Pillar)  
**Selected Tools:** OpenHands, WebVoyager, SkyPilot

---

## 🧐 Conceptual Overview
Move from "Task-Specific Agents" to **Generalist Autonomous Agents**. This layer allows LiveMirror to interact with the world outside of fixed APIs, perform complex software engineering on itself, and manage its own cloud infrastructure dynamically.

## 🚀 Key Technical Implementation Path

### 1. Advanced Engineering Loop (OpenHands)
*   **The Logic:** A highly robust agentic loop designed specifically for software development, featuring multi-step planning and self-correction.
*   **Application:** Upgrade the **Engineer Agent (EA)** on the SelfMirror Board. Instead of surgical fixes, the EA can now execute high-level architectural migrations and autonomous performance optimizations.

### 2. Visual Web Navigation (WebVoyager)
*   **The Logic:** An agent capable of operating a web browser (clicking, scrolling, typing) to extract information from websites without APIs.
*   **Application:** The "Last-Mile Scraper." The **Researcher Agent (RA)** can now verify social signals by navigating directly to source websites, checking live charts, or reading gated forum content to detect narrative deception at the source.

### 3. Cross-Cloud Workload Abstraction (SkyPilot)
*   **The Logic:** A framework that automatically launches AI workloads on any cloud (AWS, OCI, Kaggle, Colab) based on cost and GPU availability.
*   **Application:** Infrastructure Autonomy. SkyPilot will manage the deployment of our massive 72-round simulation tournaments, automatically moving the compute to the cheapest available provider in real-time.

## 🤝 Strategic Integration for Update 2.9

1.  **Expert Engineer Skill:** New skill in `src/skills/` based on OpenHands planning logic.
2.  **Web-Research Module:** Integration of WebVoyager into the `src/ingestion/` layer for non-API signals.
3.  **Universal Deployment Script:** Deployment of `scripts/cloud_deploy.yaml` using SkyPilot for Oracle/Kaggle/Colab portability.

---
**Decision:** Essential for the "10/10 Code Quality" and "Global Reach" goals. Phase 17 makes LiveMirror a self-sufficient, web-aware entity.
