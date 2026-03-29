"""
Finance-Specific Sentiment Encoder (FinBERT).
Owner: Claude

Extracts bullish, neutral, and bearish sentiment from financial text.
Used as the 4th modality in the TRIBE v2 Fusion Engine.
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import Dict, Optional, Any


class SentimentEncoder:
    """
    Expert-level financial sentiment analysis using ProsusAI/FinBERT.
    
    Trained on the Financial PhraseBank and FiQA datasets, this encoder
    outperforms generic sentiment models in market contexts.
    """
    
    def __init__(
        self,
        model_name: str = "ProsusAI/finbert",
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        device: Optional[str] = None,
    ):
        """Initialize FinBERT model and tokenizer."""
        self.model_name = model_name
        self._model = model
        self._tokenizer = tokenizer
        self._available = None
        self.device = torch.device(device) if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Mapping: 0: neutral, 1: positive, 2: negative (FinBERT spec)
        self.labels = {0: "neutral", 1: "bullish", 2: "bearish"}
        
        # Projection layer to match 384-dim fusion standard
        self.projection = nn.Linear(3, 384)  # Using logits as features (simplification)
        self.projection.to(self.device)
        
    def available(self) -> bool:
        """Check if model and weights are loaded correctly."""
        if self._available is not None:
            return self._available
            
        try:
            if self._model is None or self._tokenizer is None:
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            if hasattr(self._model, "to"):
                self._model.to(self.device)
            if hasattr(self._model, "eval"):
                self._model.eval()
            self._available = True
        except Exception:
            self._available = False
            
        return self._available
        
    def encode(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract sentiment features from text.
        
        Returns:
            {
                "label": "bullish" | "bearish" | "neutral",
                "confidence": float (0-1),
                "intensity": float (0-1),
                "embedding": np.ndarray (768,)
            }
        """
        if not text or not isinstance(text, str):
            return None
        
        if not self.available():
            return None
        
        text = text.strip()
        if not text:
            return None
            
        try:
            # 1. Tokenize and forward pass
            inputs = self._tokenizer(
                text, 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=512
            )
            
            # Move tensors to device if applicable
            inputs = {
                k: v.to(self.device) if torch.is_tensor(v) else v
                for k, v in inputs.items()
            }
            
            with torch.no_grad():
                outputs = self._model(**inputs)
            
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)
            sentiment_idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][sentiment_idx].item()
            
            # 3. Compute intensity (confidence shift from baseline 0.33)
            intensity = max(0.0, (confidence - 0.33) / 0.67)
            
            # 4. Project features to 384-dim (Fusion standard)
            with torch.no_grad():
                # Ensure projection runs on same device
                projected = self.projection(probs.to(self.device))
                embedding = projected.squeeze(0).detach().cpu().numpy()
            
            return {
                "label": self.labels.get(sentiment_idx, "neutral"),
                "confidence": round(float(confidence), 3),
                "intensity": round(float(intensity), 3),
                "embedding": embedding.astype(np.float32)
            }
        except Exception:
            return None
