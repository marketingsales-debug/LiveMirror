"""
LiveMirror Orchestrator — the master coordinator.
Owner: Claude

Ties the full loop together:
  Ingest → Score → Analyze → Graph → Simulate → Debate → Predict → Learn

This is the single entry point for running a complete prediction cycle.
Each stage feeds the next, with SSE events emitted throughout.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import numpy as np

from ..shared.types import Platform, Prediction
from ..pipeline.orchestrator import LiveMirrorPipeline
from ..simulation.engine.runner import SimulationRunner
from ..simulation.agents.factory import AgentFactory
from ..simulation.calibration.calibrator import CalibrationEngine
from ..prediction.debate import DebateEngine
from ..learning.loop import LearningLoop
from ..ingestion.platforms.reddit import RedditIngester
from ..ingestion.platforms.hackernews import HackerNewsIngester
from ..ingestion.platforms.polymarket import PolymarketIngester
from ..ingestion.platforms.web_search import WebSearchIngester


class LiveMirrorEngine:
    """
    Master orchestrator that runs the full prediction cycle.

    Usage:
        engine = LiveMirrorEngine()
        result = await engine.predict("AI regulation", agent_count=50)
        # Later, when real outcome is known:
        learning = engine.learn("pred_xxx", "Regulation passed", accuracy=0.8)
    """

    def __init__(self, seed: Optional[int] = None):
        # Core pipeline: ingest → score → analyze → graph
        self.pipeline = LiveMirrorPipeline()
        self._register_default_ingesters()

        # Simulation
        self.runner = SimulationRunner(seed=seed)
        self.factory = AgentFactory(seed=seed)

        # Prediction
        self.debate = DebateEngine()
        self.calibrator = CalibrationEngine()

        # Learning
        self.learning = LearningLoop(calibrator=self.calibrator)

        # History
        self._predictions: Dict[str, Dict[str, Any]] = {}

    def _register_default_ingesters(self) -> None:
        """Register the 4 ingesters that work without API keys."""
        self.pipeline.register_ingester(RedditIngester())
        self.pipeline.register_ingester(HackerNewsIngester())
        self.pipeline.register_ingester(PolymarketIngester())
        self.pipeline.register_ingester(WebSearchIngester())

    async def predict(
        self,
        topic: str,
        agent_count: int = 50,
        simulation_rounds: int = 72,
        emit_sse: bool = True,
        platforms: Optional[List[Platform]] = None,
        max_signals_per_platform: int = 50,
        use_fusion: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the full prediction cycle.

        Pipeline:
        1. Ingest signals from all platforms
        2. Score, analyze, and build knowledge graph
        3. Create simulation agents from graph
        4. Run multi-round simulation
        5. Run bull/bear debate
        6. Generate calibrated prediction
        7. Register prediction for future learning

        Returns:
            {
                "prediction": Prediction,
                "debate": DebateResult summary,
                "simulation": SimulationState summary,
                "pipeline": pipeline stats,
                "timing": per-stage timing,
            }
        """
        timings = {}

        # --- Stage 1: Ingest + Score + Analyze + Graph ---
        t0 = datetime.now()
        pipeline_result = await self.pipeline.run(
            topic,
            platforms=platforms,
            max_results_per_platform=max_signals_per_platform,
            emit_events=emit_sse,
        )
        timings["pipeline_ms"] = (datetime.now() - t0).total_seconds() * 1000

        scored_signals = pipeline_result["scored_signals"]

        # --- Stage 2: Create agents from graph ---
        t1 = datetime.now()
        if self.pipeline.graph.entity_count > 0:
            agents = self.factory.from_graph(
                self.pipeline.graph,
                query=topic,
                max_agents=agent_count,
                scored_signals=scored_signals,
            )
        else:
            agents = [
                self.factory.create_synthetic(name=f"Agent_{i}")
                for i in range(agent_count)
            ]
        timings["agent_creation_ms"] = (datetime.now() - t1).total_seconds() * 1000

        # --- Stage 3: Simulate ---
        t2 = datetime.now()
        state = self.runner.create_simulation(
            topic=topic,
            agents=agents,
            total_rounds=simulation_rounds,
        )
        state = await self.runner.run(state.simulation_id, emit_sse=emit_sse)
        timings["simulation_ms"] = (datetime.now() - t2).total_seconds() * 1000

        if state.error:
            return {
                "error": state.error,
                "timing": timings,
            }

        # --- Stage 3b: Emit Temporal Dynamics (Global) ---
        if emit_sse and use_fusion:
            try:
                from backend.app.api.stream import emit_temporal_update
                import numpy as np
                temporal_state = self.pipeline.fusion.temporal_transformer.compute_temporal_state(
                    self.pipeline.fusion.context_manager.get_recent()
                )
                if temporal_state:
                    await emit_temporal_update(
                        momentum=temporal_state.momentum,
                        velocity=float(np.linalg.norm(temporal_state.velocity)),
                        acceleration=float(np.linalg.norm(temporal_state.acceleration)),
                    )
            except (ImportError, Exception):
                pass

        # --- Stage 4: Debate ---
        t3 = datetime.now()
        debate_result = self.debate.debate(state)
        timings["debate_ms"] = (datetime.now() - t3).total_seconds() * 1000

        # --- Stage 5: Generate prediction ---
        correction = self.calibrator.apply_confidence_correction(
            debate_result.confidence
        ) - debate_result.confidence

        prediction = self.debate.to_prediction(
            result=debate_result,
            topic=topic,
            state=state,
            confidence_correction=correction,
        )

        # --- Stage 6: Register for learning ---
        self.learning.register_prediction(prediction)

        # Emit prediction SSE
        if emit_sse:
            try:
                from backend.app.api.stream import emit_prediction
                await emit_prediction(
                    prediction_id=prediction.prediction_id,
                    topic=prediction.topic,
                    confidence=prediction.confidence,
                )
            except ImportError:
                pass

        # Store for retrieval
        self._predictions[prediction.prediction_id] = {
            "prediction": prediction,
            "simulation_state": state,
            "debate_result": debate_result,
            "signals": scored_signals,  # Store signals for future fine-tuning
        }

        return {
            "prediction": prediction,
            "debate": {
                "direction": debate_result.direction,
                "bull_score": round(debate_result.bull_score, 3),
                "bear_score": round(debate_result.bear_score, 3),
                "consensus": round(debate_result.consensus, 3),
                "bull_count": len(debate_result.bull_arguments),
                "bear_count": len(debate_result.bear_arguments),
                "neutral_count": debate_result.neutral_count,
            },
            "simulation": {
                "simulation_id": state.simulation_id,
                "rounds": state.total_rounds,
                "agents": len(state.agents),
                "actions": len(state.actions),
                "final_sentiment": round(state.topic_sentiment, 3),
            },
            "pipeline": pipeline_result.get("timing", {}),
            "timing": timings,
        }

    def learn(
        self,
        prediction_id: str,
        actual_outcome: str,
        accuracy: float,
    ) -> Dict[str, Any]:
        """
        Feed real-world outcome back into the system.

        This is the self-improving loop:
        1. Compare prediction against what actually happened
        2. Adjust agent behavioral fingerprints
        3. Update confidence calibration curve
        4. Next prediction cycle uses adjusted parameters
        """
        stored = self._predictions.get(prediction_id)
        sim_state = stored["simulation_state"] if stored else None
        signals = stored["signals"] if stored else []

        # --- Trigger Fusion Fine-Tuning (Roadmap Phase 2) ---
        if signals and self.pipeline.fusion.config.use_learned_attention:
            # Simple heuristic: target is a bullish (+1) or bearish (-1) vector
            # based on the validated accuracy and direction.
            direction_vec = np.ones(384, dtype=np.float32) if accuracy > 0.5 else np.zeros(384, dtype=np.float32)
            
            # Encode signals to embeddings first
            encoded_inputs = []
            for s in signals[:10]:
                modality_emb = self.pipeline.fusion.text_encoder.encode(s.signal.content)
                if modality_emb is not None:
                    # Extract raw embedding from ModalityEmbedding object
                    encoded_inputs.append({"text": modality_emb.embedding})
            
            if encoded_inputs:
                targets = [direction_vec for _ in range(len(encoded_inputs))]
                self.pipeline.fusion.fine_tune_attention(encoded_inputs, targets)

        return self.learning.validate_and_calibrate(
            prediction_id=prediction_id,
            actual_outcome=actual_outcome,
            accuracy_score=accuracy,
            simulation_state=sim_state,
        )

    @property
    def stats(self) -> Dict[str, Any]:
        """Current engine statistics."""
        return {
            "predictions_made": len(self._predictions),
            "platforms_registered": len(self.pipeline.ingestion.available_platforms),
            "graph_entities": self.pipeline.graph.entity_count,
            "graph_edges": self.pipeline.graph.edge_count,
            "learning": self.learning.stats,
        }
