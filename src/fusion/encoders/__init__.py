"""
Encoder implementations for multimodal fusion.
Owner: Claude

- TextEncoder: Wraps SemanticScorer for 384-dim embeddings
- AudioEncoder: Whisper + librosa (graceful fallback)
- VideoEncoder: CLIP ViT-B/32 frame analysis
"""

from .text import TextEncoder
from .registry import EncoderRegistry

__all__ = ["TextEncoder", "EncoderRegistry"]
