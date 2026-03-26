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

### 2026-03-27 — AI Ownership Split
- **Decision:** Claude owns backend/ingestion/graph/simulation/learning. Gemini owns analysis/visualization/dashboard/frontend.
- **Reasoning:** Claude has stronger backend/architecture strengths. Gemini handles frontend/analysis. Clear boundaries prevent conflicts.
- **Alternatives:** Random split (bad), feature-based split (too many merge conflicts)
- **Decided by:** human + claude
