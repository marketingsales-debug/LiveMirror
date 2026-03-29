"""
Unit tests for FusionPipeline end-to-end.
Owner: Claude
"""

import pytest
from src.fusion.pipeline import FusionPipeline
from src.fusion.types import FusionConfig


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
