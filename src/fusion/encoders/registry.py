"""
Encoder Registry — manages available encoders.
Owner: Claude
"""

from typing import Dict, Optional
from .text import TextEncoder


class EncoderRegistry:
    """Registry of available encoders by modality."""
    
    def __init__(self):
        """Initialize with text encoder (always available)."""
        self._encoders: Dict[str, object] = {
            "text": TextEncoder(),
        }
        self._audio_encoder: Optional[object] = None
        self._video_encoder: Optional[object] = None
    
    def register(self, modality: str, encoder: object) -> None:
        """Register an encoder for a modality."""
        self._encoders[modality] = encoder
    
    def get(self, modality: str) -> Optional[object]:
        """Get encoder for modality (returns None if unavailable)."""
        return self._encoders.get(modality)
    
    def available(self, modality: str) -> bool:
        """Check if encoder is available."""
        encoder = self.get(modality)
        if encoder is None:
            return False
        # Check if encoder has available() method
        if hasattr(encoder, "available"):
            return encoder.available()
        return True
