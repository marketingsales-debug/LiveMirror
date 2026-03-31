# LiveMirror — Architecture Decision Log

All decisions that affect both AIs are logged here. Append-only.

---

### 2026-03-27 — Project Tech Stack
- **Decision:** Python (FastAPI) backend, Vue.js (Vite) frontend, TypeScript shared types
- **Reasoning:** MiroFish uses this stack, maintaining compatibility. FastAPI is async-native for real-time data. Vue.js is lightweight for dashboards.
- **Alternatives:** Next.js (too heavy), Flask (no async), React (team familiarity lower)
- **Decided by:** human + claude

### 2026-03-27 — Collaboration Protocol
- **Decision:** File-based communication via .collab/ directory with ownership-based separation
- **Reasoning:** Claude and Gemini cannot communicate directly. Files in the repo serve as the communication channel. CODEOWNERS prevents merge conflicts.
- **Alternatives:** Database-backed coordination (overkill for v1), API-based (requires server)
- **Decided by:** human + claude

### 2026-03-27 — Knowledge Graph Backend
- **Decision:** Zep Cloud for v1, with Neo4j migration path for scale
- **Reasoning:** MiroFish already uses Zep Cloud with GraphRAG. Keeps compatibility. Neo4j is the upgrade path when we need more than 10K entities.
- **Alternatives:** Neo4j from day 1 (more setup), Amazon Neptune (vendor lock), plain PostgreSQL (no graph queries)
- **Decided by:** human + claude

### 2026-03-27 — Simulation Engine
- **Decision:** OASIS (CAMEL-AI) as base, with custom calibration layer on top
- **Reasoning:** MiroFish uses OASIS for multi-agent social simulation. We add a calibration layer that feeds real-world data back into agent behavior.
- **Alternatives:** Custom simulation from scratch (too slow), Mesa (less social-media focused)
- **Decided by:** human + claude

### 2026-03-28 — Dashboard API Integration & Predict Wiring
- **Decision:** Split dashboard controls into three distinct phase buttons (Ingest, Simulate, Predict) rather than a single master 'Run All' button, while retaining the unified `/api/predict/start` for the full pipeline. Also introduced `<DebatePanel>` to handle the rich debate statistics.
- **Reasoning:** A single monolith button obscures the distinct architectural phases (Phase 1 Ingest, Phase 3 Simulate, Phase 5 Debate). Exposing all three cleanly allows users to demonstrate the engine effectively. The `DebatePanel` isolates the UI logic for the bull/bear consensus visualization, fetching `/api/predict/report/{id}` on an SSE trigger to avoid crowding `DashboardView.vue` with layout logic.
- **Alternatives:** Just replacing "Run Simulation" with "Run Prediction" (reduces user control). Adding webSockets (overkill, SSE works well).
- **Decided by:** gemini

### 2026-03-28 — Dashboard Phase 6 Learning Loop UI
- **Decision:** Integrated `PlatformHealth`, `LearningStatsPanel`, and `PredictionHistory` into `DashboardView.vue`. `PlatformHealth` placed in sidebar. History given a new full-width row at bottom.
- **Reasoning:** Showcases the new orchestrator directly. PredictionHistory has inline validation actions `POST /api/predict/validate` to easily demonstrate the self-improving engine without leaving the dashboard.
- **Alternatives:** A separate "/history" page. (Rejected: Dashboard should be a single pane of glass).
- **Decided by:** gemini
