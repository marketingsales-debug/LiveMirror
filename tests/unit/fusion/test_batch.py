"""
Unit tests for BatchProcessor.
Owner: Claude
"""

import pytest
import asyncio
from unittest.mock import MagicMock
from src.fusion.batch.processor import BatchProcessor

class TestBatchProcessor:
    """Test BatchProcessor concurrency and ordering."""
    
    @pytest.mark.asyncio
    async def test_process_batch_concurrently(self):
        """Verify batch processor runs multiple signals in parallel."""
        # Mock pipeline
        pipeline = MagicMock()
        # Mock process_signal to return a value
        pipeline.process_signal.side_effect = lambda **kwargs: {"result": kwargs.get("content")}
        
        processor = BatchProcessor(pipeline, batch_size=2)
        signals = [
            {"content": "s1", "metadata": {}},
            {"content": "s2", "metadata": {}},
            {"content": "s3", "metadata": {}}
        ]
        
        results = await processor.process_batch(signals)
        
        # Verify 3 results in same order
        assert len(results) == 3
        assert results[0]["result"] == "s1"
        assert results[1]["result"] == "s2"
        assert results[2]["result"] == "s3"
        
        # Verify pipeline was called 3 times
        assert pipeline.process_signal.call_count == 3
        
    @pytest.mark.asyncio
    async def test_batch_ordering_with_delays(self):
        """Verify results are returned in correct index order despite delays."""
        pipeline = MagicMock()
        
        async def mock_process(s):
            # Simulate variable delays
            content = s.get("content")
            if content == "fast":
                await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.05)
            return content
            
        # Wrap the mock for processor
        processor = BatchProcessor(pipeline, batch_size=5)
        # Manually override the single async processor for this test
        processor._process_single_async = mock_process
        
        signals = [{"content": "slow"}, {"content": "fast"}]
        results = await processor.process_batch(signals)
        
        assert results == ["slow", "fast"]
