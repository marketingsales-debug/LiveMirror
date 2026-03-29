"""
Unit tests for SentimentEncoder.
Owner: Claude
"""

import numpy as np
import torch
from src.fusion.encoders.sentiment import SentimentEncoder


class DummyTokenizer:
    def __call__(self, text, return_tensors, padding, truncation, max_length):
        return {
            "input_ids": torch.tensor([[1, 2]]),
            "attention_mask": torch.tensor([[1, 1]])
        }


class DummyModel:
    def __init__(self, logits=None):
        self._logits = logits if logits is not None else torch.zeros((1, 3))
        self.eval_called = False
        self.to_called = False

    def to(self, device):
        self.to_called = True
        return self

    def eval(self):
        self.eval_called = True
        return self

    def __call__(self, **kwargs):
        return type("Out", (), {"logits": self._logits})


class TestSentimentEncoder:
    """Test SentimentEncoder classification and availability."""

    def test_available_uses_injected_components(self):
        """Availability is true when model/tokenizer are provided."""
        model = DummyModel()
        tokenizer = DummyTokenizer()
        encoder = SentimentEncoder(model=model, tokenizer=tokenizer)

        assert encoder.available() is True
        assert model.eval_called is True

    def test_available_handles_load_failure(self, monkeypatch):
        """Gracefully reports unavailable when load fails."""
        def raise_load(*args, **kwargs):
            raise RuntimeError("load failed")

        monkeypatch.setattr("src.fusion.encoders.sentiment.AutoTokenizer.from_pretrained", raise_load)
        monkeypatch.setattr("src.fusion.encoders.sentiment.AutoModelForSequenceClassification.from_pretrained", raise_load)

        encoder = SentimentEncoder()
        assert encoder.available() is False

    def test_encode_returns_structured_output(self):
        """Encodes text with FinBERT-style logits and projects embedding."""
        logits = torch.tensor([[0.1, 2.0, -0.5]])  # index 1 -> bullish
        model = DummyModel(logits=logits)
        tokenizer = DummyTokenizer()
        encoder = SentimentEncoder(model=model, tokenizer=tokenizer, device="cpu")

        result = encoder.encode("Earnings exceeded expectations")

        assert result is not None
        assert result["label"] == "bullish"
        assert 0.0 <= result["confidence"] <= 1.0
        assert 0.0 <= result["intensity"] <= 1.0
        assert result["embedding"].shape == (384,)
        assert result["embedding"].dtype == np.float32

    def test_encode_handles_empty_and_unavailable(self):
        """Returns None when input is empty or model unavailable."""
        encoder = SentimentEncoder()
        encoder._available = False
        assert encoder.encode("") is None
        assert encoder.encode(None) is None
