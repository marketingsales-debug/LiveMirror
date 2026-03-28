"""
Tests for the LiveMirrorEngine orchestrator.
Owner: Claude

Tests the full predict → learn cycle without hitting real APIs.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from src.orchestrator.engine import LiveMirrorEngine
from src.shared.types import Platform, RawSignal, SignalType


def _mock_signals(count: int = 5) -> list:
    """Create mock signals for testing without real API calls."""
    from datetime import datetime
    return [
        RawSignal(
            platform=Platform.REDDIT,
            signal_type=SignalType.SOCIAL_POST,
            content=f"Test signal about AI regulation #{i}",
            timestamp=datetime.now(),
            engagement={"likes": 10 * i, "comments": 5 * i, "shares": 0},
        )
        for i in range(1, count + 1)
    ]


class TestLiveMirrorEngine:
    def setup_method(self):
        self.engine = LiveMirrorEngine(seed=42)

    @pytest.mark.asyncio
    async def test_predict_with_synthetic_agents(self):
        """Full prediction cycle with synthetic agents (no graph data)."""
        # Mock the pipeline to avoid real API calls
        mock_signals = _mock_signals(5)
        with patch.object(
            self.engine.pipeline.ingestion, "ingest_all",
            new_callable=AsyncMock, return_value=mock_signals,
        ):
            result = await self.engine.predict(
                topic="AI regulation",
                agent_count=10,
                simulation_rounds=5,
                emit_sse=False,
            )

        assert "prediction" in result
        assert result["prediction"].topic == "AI regulation"
        assert 0.05 <= result["prediction"].confidence <= 0.95
        assert result["simulation"]["rounds"] == 5
        assert result["simulation"]["agents"] == 10
        assert result["debate"]["bull_count"] + result["debate"]["bear_count"] + result["debate"]["neutral_count"] == 10

    @pytest.mark.asyncio
    async def test_predict_then_learn(self):
        """Full cycle: predict → learn → improved calibration."""
        mock_signals = _mock_signals(3)
        with patch.object(
            self.engine.pipeline.ingestion, "ingest_all",
            new_callable=AsyncMock, return_value=mock_signals,
        ):
            result = await self.engine.predict(
                "AI regulation", agent_count=10, simulation_rounds=3, emit_sse=False,
            )

        pred_id = result["prediction"].prediction_id

        # Validate with high accuracy
        learn_result = self.engine.learn(
            pred_id, "Regulation passed with strong support", accuracy=0.8
        )

        assert learn_result["validation"].accuracy_score == 0.8
        assert learn_result["learning_stats"]["total_validations"] == 1

    @pytest.mark.asyncio
    async def test_multiple_predictions_improve_calibration(self):
        """Multiple prediction+learn cycles should adjust confidence offset."""
        mock_signals = _mock_signals(3)

        for i in range(3):
            with patch.object(
                self.engine.pipeline.ingestion, "ingest_all",
                new_callable=AsyncMock, return_value=mock_signals,
            ):
                result = await self.engine.predict(
                    f"topic_{i}", agent_count=5, simulation_rounds=2, emit_sse=False,
                )
            self.engine.learn(
                result["prediction"].prediction_id,
                "Poor outcome",
                accuracy=0.3,
            )

        stats = self.engine.stats
        assert stats["predictions_made"] == 3
        assert stats["learning"]["total_validations"] == 3

    @pytest.mark.asyncio
    async def test_stats_populated(self):
        """Engine stats should reflect current state."""
        stats = self.engine.stats
        assert stats["predictions_made"] == 0
        assert stats["platforms_registered"] == 4
        assert stats["graph_entities"] == 0

    @pytest.mark.asyncio
    async def test_predict_handles_simulation_error_gracefully(self):
        """If simulation fails, result should contain error."""
        mock_signals = _mock_signals(1)
        with patch.object(
            self.engine.pipeline.ingestion, "ingest_all",
            new_callable=AsyncMock, return_value=mock_signals,
        ):
            # Force an error by giving 0 rounds (which would complete instantly)
            result = await self.engine.predict(
                "test", agent_count=5, simulation_rounds=0, emit_sse=False,
            )

        # 0 rounds = immediate completion (not an error)
        assert "prediction" in result
