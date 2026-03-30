# Research Audit: TikTok-Api (David Teather)
**Status:** Ingestion Upgrade for Update 2.9 (The "High-Velocity" Pillar)  
**Reference:** [davidteather/TikTok-Api](https://github.com/davidteather/TikTok-Api)

---

## 🧐 Conceptual Overview
Moves from generic scraping to a specialized, Playwright-based browser-in-the-loop wrapper. This is essential for bypassing TikTok's advanced bot detection (msToken, verify_fp) and extracting high-fidelity metadata.

## 🚀 Key Technical Insights

### 1. Browser-in-the-Loop Execution
*   **The Logic:** Uses Playwright to run a headless browser that executes TikTok's signature generation scripts.
*   **The Result:** Requests are cryptographically signed, making them virtually indistinguishable from real human browser traffic.

### 2. Async Multi-Session Scaling
*   **The Logic:** Built on `asyncio` with support for rotating session factories and proxies.
*   **The Result:** Enables the high-velocity ingestion needed for our 10,000-agent swarm simulations.

### 3. Deep Metadata Extraction
*   **The Logic:** Accesses internal API fields like view count velocity and sound ID usage.
*   **The Result:** Provides the raw "Numerical DNA" required for our **Delta Analyzer** to detect tipping points.

## 🤝 Strategic Integration for Update 2.9

1.  **Ingestion Rewrite:** Refactor `src/ingestion/platforms/tiktok.py` to use the `TikTokApi` async client.
2.  **Visual Modality Prep:** Use the library to download `.mp4` sources for **Moondream** visual sentiment analysis.
3.  **Dependency Sync:** Added `TikTokApi` and `playwright` to the v2.0 stack.

---
**Decision:** Mission-critical for high-fidelity social signal extraction.
