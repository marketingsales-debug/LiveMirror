# ADR-001: LiveMirror Project Overview

## Status: ACCEPTED
## Date: 2026-03-27

## Context

We need a system that combines real-time data ingestion (like last30days)
with multi-agent simulation (like MiroFish) to create a self-calibrating
prediction engine.

## Decision

Build LiveMirror as a 6-layer architecture:

1. **DATA LAYER** — Real-time ingestion from 10+ social platforms,
   economic signals, government feeds, physical world sensors
2. **INTELLIGENCE LAYER** — Emotional contagion engine, narrative DNA
   analyzer, cultural context modules, platform physics engine,
   multi-agent debate system
3. **SIMULATION LAYER** — Evolving agent personas, calibrated forward
   simulation (OASIS-based), counter-simulation (red team), temporal
   memory (5-layer), coalition/trust network dynamics
4. **LEARNING LAYER** — Prediction validation loop, self-healing
   auto-diagnosis, confidence calibration, behavioral fingerprint
   updating from real data
5. **OUTPUT LAYER** — Real-time dashboard, cited briefings, scenario
   testing interface, multiplayer collaboration rooms, developer API
6. **TRUST LAYER** — Audit trail, bias detection, privacy-preserving
   aggregation, ethical guardrails

## Tech Stack

- Backend: Python 3.11+ / FastAPI
- Frontend: Vue.js / Vite / D3.js
- Simulation: OASIS (CAMEL-AI) with custom calibration
- Knowledge Graph: Zep Cloud (GraphRAG), Neo4j migration path
- LLM: OpenAI-compatible API (any provider)
- Storage: PostgreSQL + TimescaleDB (time-series predictions)
- Deployment: Docker

## AI Collaboration

Two AIs build this project together:
- Claude (Claude Code): backend, ingestion, graph, simulation, learning
- Gemini (Gemini CLI): analysis, visualization, dashboard, frontend

Communication via `.collab/` directory protocol.

## Consequences

- Clear separation of concerns across 6 layers
- Two-AI collaboration requires strict ownership and handoff protocol
- OASIS dependency means Python 3.11-3.12 requirement
- Zep Cloud dependency requires API key (free tier available)
