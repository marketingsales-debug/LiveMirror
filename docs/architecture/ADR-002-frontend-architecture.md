# ADR 002: Frontend Architecture

## Status
Accepted

## Context
Claude established the LiveMirror backend to use Python FastAPI. As part of my role (Gemini), I am responsible for frontend decisions to support real-time data flow, state management, and aesthetic presentation.

## Decision
We will construct the frontend using:
1. **Vue 3 (Composition API) + Vite**: Vite provides ultra-fast HMR critical for iterating on visualization. Composition API integrates seamlessly with TS.
2. **TypeScript**: Provides rigorous safety. I translated Claude's shared Python typing equivalents to TS inside `src/shared/types/`.
3. **Vanilla CSS variables + Glassmorphism**: Forgoing heavy unstyled component libraries because the requirement calls for bespoke "cyberpunk/modern" tracking aesthetics. 
4. **D3.js Visualization layer**: Selected over ECharts or Chart.js for building raw network graph simulation nodes. ECharts abstract away the physics engines required for "Contagion networking."

## Consequences
- Requires strict synchronization of `src/shared/types` to ensure Python and TS types align. Any change from Claude requires a cross-language update.
- D3 Force layouts are CPU intensive; performance monitoring on graphs > 1000 nodes will be required down the line.
