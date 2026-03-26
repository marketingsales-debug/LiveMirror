"""
End-to-end pipeline: Ingestion → Scoring → Analysis → Graph → SSE
Owner: Claude

This is the main orchestration loop that:
1. Searches all platforms for a query
2. Scores and deduplicates signals
3. Runs each signal through Gemini's analysis pipeline
4. Feeds results into the knowledge graph
5. Emits SSE events at each stage for the frontend
"""

import asyncio
from typing import List, Optional
from datetime import datetime

from ..shared.types import Platform, ScoredSignal
from ..ingestion.manager import IngestionManager
from ..ingestion.scorer import SignalScorer
from ..analysis.pipeline import AnalysisPipeline, AnalysisResult
from ..graph.knowledge.graph import KnowledgeGraph


class LiveMirrorPipeline:
    """
    Orchestrates the full ingestion → analysis → graph pipeline.

    Usage:
        pipeline = LiveMirrorPipeline()
        pipeline.register_ingester(RedditIngester())
        results = await pipeline.run("AI regulation")
    """

    def __init__(
        self,
        scorer: Optional[SignalScorer] = None,
        analysis: Optional[AnalysisPipeline] = None,
        graph: Optional[KnowledgeGraph] = None,
    ):
        self.ingestion = IngestionManager()
        self.scorer = scorer or SignalScorer()
        self.analysis = analysis or AnalysisPipeline()
        self.graph = graph or KnowledgeGraph()
        self._last_run_stats = {}

    def register_ingester(self, ingester) -> None:
        """Register a platform ingester."""
        self.ingestion.register(ingester)

    async def run(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        max_results_per_platform: int = 50,
        emit_events: bool = True,
    ) -> dict:
        """
        Execute the full pipeline for a query.

        Returns:
            {
                "query": str,
                "scored_signals": List[ScoredSignal],
                "analysis_results": List[AnalysisResult],
                "graph_stats": dict,
                "timing": dict,
            }
        """
        timings = {}

        # --- 1. Ingest from all platforms ---
        t0 = datetime.now()
        raw_signals = await self.ingestion.ingest_all(
            query, platforms, max_results_per_platform=max_results_per_platform
        )
        timings["ingestion_ms"] = (datetime.now() - t0).total_seconds() * 1000

        if emit_events:
            await self._emit_ingestion_progress(raw_signals, query)

        # --- 2. Score and rank ---
        t1 = datetime.now()
        scored = self.scorer.score_all(raw_signals, query)
        timings["scoring_ms"] = (datetime.now() - t1).total_seconds() * 1000

        # --- 3. Analyze each signal through Gemini's pipeline ---
        t2 = datetime.now()
        analysis_results: List[AnalysisResult] = []
        for s in scored[:50]:  # cap at top 50 to avoid overload
            cross_platform = s.cross_platform_score > 0
            age_hours = self.scorer._hours_since(s.signal.timestamp)
            result = self.analysis.process(s, age_hours=age_hours, cross_platform=cross_platform)
            analysis_results.append(result)

            if emit_events:
                await self._emit_analysis(result)

        timings["analysis_ms"] = (datetime.now() - t2).total_seconds() * 1000

        # --- 4. Feed into knowledge graph ---
        t3 = datetime.now()
        graph_stats = self.graph.ingest_signals(scored, query)
        timings["graph_ms"] = (datetime.now() - t3).total_seconds() * 1000

        if emit_events:
            await self._emit_graph(graph_stats)
            await self._emit_complete(query, scored)

        self._last_run_stats = {
            "query": query,
            "raw_signals": len(raw_signals),
            "scored_signals": len(scored),
            "analysis_results": len(analysis_results),
            "graph_entities": self.graph.entity_count,
            "graph_edges": self.graph.edge_count,
            "timing": timings,
        }

        return {
            "query": query,
            "scored_signals": scored,
            "analysis_results": analysis_results,
            "graph_stats": graph_stats,
            "timing": timings,
        }

    @property
    def stats(self) -> dict:
        return self._last_run_stats

    # --- SSE helpers (lazy import to avoid circular deps) ---

    async def _emit_ingestion_progress(self, signals, query):
        try:
            from backend.app.api.stream import emit_ingestion_progress
            platform_counts = {}
            for s in signals:
                p = s.platform.value
                platform_counts[p] = platform_counts.get(p, 0) + 1
            total = len(signals)
            for platform, count in platform_counts.items():
                await emit_ingestion_progress(platform, count, total)
        except ImportError:
            pass

    async def _emit_analysis(self, result: AnalysisResult):
        try:
            from backend.app.api.stream import emit_analysis_result
            await emit_analysis_result(
                signal_id=result.signal_id,
                platform=result.platform,
                sentiment_score=result.sentiment_score,
                emotional_velocity=result.emotional_velocity,
                is_tipping_point=result.is_tipping_point,
                narrative_stage=result.narrative_stage.value,
                fingerprint=result.fingerprint,
            )
        except ImportError:
            pass

    async def _emit_graph(self, stats):
        try:
            from backend.app.api.stream import emit_graph_update
            await emit_graph_update(
                entities_created=stats.get("entities_created", 0),
                edges_created=stats.get("edges_created", 0),
                total_entities=self.graph.entity_count,
                total_edges=self.graph.edge_count,
            )
        except ImportError:
            pass

    async def _emit_complete(self, query, scored):
        try:
            from backend.app.api.stream import emit_ingestion_complete
            top_score = scored[0].composite_score if scored else 0.0
            platforms = len({s.signal.platform for s in scored})
            await emit_ingestion_complete(query, len(scored), platforms, top_score)
        except ImportError:
            pass
