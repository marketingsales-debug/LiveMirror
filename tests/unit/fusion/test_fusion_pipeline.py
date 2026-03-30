"""
Unit tests for FusionPipeline end-to-end.
Owner: Claude
"""

import logging
import numpy as np
import pytest
from src.fusion.pipeline import FusionPipeline
from src.fusion.types import FusionConfig, ModalityEmbedding


class TestFusionPipeline:
    """Test end-to-end fusion pipeline."""
    
    def test_pipeline_initialization(self):
        """Pipeline initializes correctly."""
        config = FusionConfig()
        pipeline = FusionPipeline(config)
        
        assert pipeline.config is not None
        assert pipeline.text_encoder is not None
        assert pipeline.audio_encoder is not None
        assert pipeline.video_encoder is not None
    
    def test_process_signal_text_only(self):
        """Process text-only signal."""
        config = FusionConfig(enable_audio=False, enable_video=False)
        pipeline = FusionPipeline(config)
        
        prediction = pipeline.process_signal(
            content="Bitcoin is rallying",
            platform="twitter",
            engagement={"likes": 100, "comments": 10},
        )
        
        assert prediction is not None
        assert len(prediction.segment_predictions) > 0
        assert -1.0 <= prediction.consensus_direction <= 1.0
    
    def test_process_signal_with_engagement(self):
        """Prediction accounts for engagement."""
        config = FusionConfig(enable_audio=False, enable_video=False)
        pipeline = FusionPipeline(config)
        
        engagement = {"likes": 1000, "comments": 100, "shares": 50}
        prediction = pipeline.process_signal(
            content="Great news",
            platform="reddit",
            engagement=engagement,
        )
        
        assert prediction is not None
        assert prediction.consensus_confidence >= 0.0
    
    def test_context_window_accumulation(self):
        """Context window accumulates states."""
        config = FusionConfig(enable_audio=False, enable_video=False)
        pipeline = FusionPipeline(config)
        
        # Process multiple signals
        for i in range(5):
            pipeline.process_signal(
                content=f"Signal {i}",
                platform="twitter",
            )
        
        states = pipeline.context_manager.get_recent()
        assert len(states) == 5

    def test_process_signal_logs_and_returns_none_on_exception(self, monkeypatch, caplog):
        """Exceptions are logged and return None."""
        config = FusionConfig(enable_audio=False, enable_video=False)
        pipeline = FusionPipeline(config)

        def boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(pipeline.text_encoder, "encode", boom)

        with caplog.at_level(logging.ERROR):
            result = pipeline.process_signal(content="bad input")

        assert result is None
        assert any("Fusion pipeline processing failed" in record.message for record in caplog.records)

    def test_process_signal_returns_none_for_invalid_fused_embedding(self, monkeypatch, caplog):
        """Invalid fused embeddings are rejected."""
        config = FusionConfig(enable_audio=False, enable_video=False, use_learned_attention=False)
        pipeline = FusionPipeline(config)

        def fake_encode(_content: str):
            return ModalityEmbedding("text", np.ones(384, dtype=np.float32))

        monkeypatch.setattr(pipeline.text_encoder, "encode", fake_encode)
        monkeypatch.setattr(pipeline.cross_modal_fixed, "fuse", lambda _embeddings: None)

        with caplog.at_level(logging.WARNING):
            result = pipeline.process_signal(content="hello")

        assert result is None
        assert any("Fused embedding invalid" in record.message for record in caplog.records)
