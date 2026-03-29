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
    
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        """Initialize FinBERT model and tokenizer."""
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._available = None
        
        # Mapping: 0: neutral, 1: positive, 2: negative
        # (FinBERT's specific index mapping)
        self.labels = {0: "bullish", 1: "bearish", 2: "neutral"}
        
        # Projection layer to match 384-dim fusion standard
        self.projection = nn.Linear(3, 384) # Using logits as features (simplification)
        
    def available(self) -> bool:
        """Check if model and weights are loaded correctly."""
        if self._available is not None:
            return self._available
            
        try:
            if self._model is None:
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
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
        if not self.available() or not text:
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
            
            with torch.no_grad():
                outputs = self._model(**inputs)
                
            # 2. Extract probabilities
            probs = torch.softmax(outputs.logits, dim=1)
            sentiment_idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][sentiment_idx].item()
            
            # 3. Compute intensity (confidence shift from baseline 0.33)
            intensity = max(0.0, (confidence - 0.33) / 0.67)
            
            # 4. Project features to 384-dim (Fusion standard)
            # Using softmax probabilities mapped to latent space
            # In a full model, we'd use the hidden states (768) -> 384
            with torch.no_grad():
                embedding = self.projection(probs).squeeze(0).detach().numpy()
            
            return {
                "label": self.labels.get(sentiment_idx, "neutral"),
                "confidence": round(float(confidence), 3),
                "intensity": round(float(intensity), 3),
                "embedding": embedding.astype(np.float32)
            }
        except Exception:
            return None
