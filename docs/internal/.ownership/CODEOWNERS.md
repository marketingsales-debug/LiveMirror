# LiveMirror — Code Ownership Map

## Claude Owns (Backend + Core Engine)
```
src/ingestion/          → Claude (data ingestion from all platforms)
src/graph/              → Claude (knowledge graph, entity management)
src/simulation/         → Claude (OASIS engine, agent simulation)
src/learning/           → Claude (prediction validation, calibration)
backend/                → Claude (FastAPI server, API logic)
scripts/orchestrator.py → Claude (multi-AI orchestrator)
config/                 → Claude (server/engine configuration)
```

## Gemini Owns (Analysis + Frontend + Visualization)
```
src/analysis/           → Gemini (sentiment, narrative, emotional, cultural)
src/visualization/      → Gemini (graphs, charts, real-time viz)
src/dashboard/          → Gemini (dashboard UI components)
frontend/               → Gemini (Vue.js app, all frontend code)
```

## Shared (Lock Protocol Required — see RULES.md Rule 3)
```
src/shared/             → Lock required (shared types, interfaces, utilities)
src/api/                → Lock required (API routes used by both)
```

## Both Can Write (Append-Only / Own Section)
```
.collab/                → Both (collaboration files, append-only)
docs/architecture/      → Both (ADR files, each AI writes their own)
tests/adversarial/claude-tests/  → Claude writes (tests to break Gemini's code)
tests/adversarial/gemini-tests/  → Gemini writes (tests to break Claude's code)
tests/unit/             → Owner of source code writes their unit tests
tests/integration/      → Both (integration tests touching both sides)
```

## Human Only
```
.collab/CONFLICTS.md    → Human resolves (AIs log conflicts, human decides)
main branch             → Human merges (AIs work on feature branches)
```
