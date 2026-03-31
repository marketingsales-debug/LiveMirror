# Claude Review — Gemini Analysis Layer

**Reviewer:** Claude
**Date:** 2026-03-27
**Branch:** `gemini/analysis-layer`
**Verdict:** APPROVED with issues noted

---

## Files Reviewed

### 1. `src/analysis/sentiment/analyzer.py` — SentimentAnalyzer

**Strengths:**
- Clean interface: `analyze(text, platform, context) -> float`
- Platform-specific calibration (Reddit amplification, Twitter negativity bias) is smart
- `batch_analyze` convenience method is useful
- Output clamped to [-1.0, 1.0] — good

**Issues:**

| Severity | Issue | Details |
|----------|-------|---------|
| **HIGH** | Keyword set too small | Only 7 positive + 7 negative words. "horrible", "amazing", "pump", "dump", "moon", "rekt" all return 0.0 |
| **HIGH** | Whitespace-split tokenization | `"great!"` won't match "great" because of punctuation. `"not great"` scores positive (ignores negation) |
| **MEDIUM** | `use_llm` flag is dead code | Constructor accepts it but never uses it — confusing API surface |
| **MEDIUM** | No neutral detection | Everything that's not in the word lists returns 0.0 — can't distinguish neutral from unknown |
| **LOW** | Missing `__init__.py` | No package init files in analysis subdirectories |

**Recommendation:** Replace keyword matching with VADER (3-line integration, handles negation + punctuation + emojis) as an interim before LLM scoring.

---

### 2. `src/analysis/emotional/contagion.py` — EmotionalContagionTracker

**Strengths:**
- Velocity calculation via time-windowed halves is elegant
- Tipping point detection is simple and testable
- Configurable threshold

**Issues:**

| Severity | Issue | Details |
|----------|-------|---------|
| **HIGH** | `datetime.now()` in `calculate_emotional_velocity` | Untestable — can't control "now" in tests. Should accept `now` parameter or use injected clock |
| **HIGH** | Unbounded memory growth | `sentiment_history` list grows forever. No pruning, no max size. Will OOM on production workloads |
| **MEDIUM** | No platform-level velocity | Calculates global velocity only. Can't detect "Twitter is angry but Reddit is calm" |
| **MEDIUM** | Type hint uses lowercase `any` | `List[Dict[str, any]]` should be `List[Dict[str, Any]]` (capital A) |
| **LOW** | No thread safety | Multiple async tasks recording simultaneously could corrupt the list |

**Recommendation:** Add a `max_history` parameter with LRU eviction. Accept `now` as optional parameter for testability.

---

### 3. `src/analysis/narrative/dna.py` — NarrativeDNAAnalyzer

**Strengths:**
- Historical fingerprint concept is creative
- Stage identification logic is reasonable for a first pass
- Uses shared `NarrativeStage` enum — good type alignment

**Issues:**

| Severity | Issue | Details |
|----------|-------|---------|
| **HIGH** | Stage gaps create wrong defaults | `identify_stage(age_hours=24, engagement=3000, velocity=0.5)` falls through all conditions → returns EARLY_SPREAD, which is wrong (should be something like GROWTH) |
| **HIGH** | `match_fingerprint` thresholds don't align with `historical_fingerprints` | Fingerprint says outrage_cascade velocity is -0.6, but matcher triggers at -0.4. Fingerprint says viral_support velocity is 0.5, matcher triggers at 0.4 |
| **MEDIUM** | No PEAK or RESOLUTION stages in identify_stage | These NarrativeStage values are never returned |
| **LOW** | Hardcoded thresholds | Magic numbers everywhere (2 hours, 12 hours, 1000 engagement, etc.) should be configurable |

**Recommendation:** Add explicit conditions for PEAK and RESOLUTION stages. Align fingerprint definitions with matcher thresholds. Make thresholds configurable.

---

## Integration Assessment

**Compatibility with Ingestion Output:**
- `SentimentAnalyzer.analyze()` expects `str` + `Platform` — matches `RawSignal.content` + `RawSignal.platform` ✓
- `EmotionalContagionTracker.record_sentiment()` expects `text_id`, `platform` (str), `sentiment_score`, `timestamp` — we can derive all from `ScoredSignal` ✓
- `NarrativeDNAAnalyzer.identify_stage()` expects `age_hours`, `total_engagement`, `velocity` — we can compute from scored signals ✓

**Overall:** Good heuristic foundation. The modules integrate cleanly with ingestion output. The main gaps are robustness (edge cases, memory growth) rather than design.
