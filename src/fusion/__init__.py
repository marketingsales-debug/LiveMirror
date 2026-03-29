"""
Multimodal Fusion Layer — TRIBE v2-Inspired Architecture
Owner: Claude

Combines text, audio, and video signals with cross-modal attention,
temporal modeling, and multi-audience prediction heads.

Modules:
- types: Core data structures
- encoders: Text, audio, video encoder implementations
- attention: Cross-modal and temporal attention mechanisms
- context: Temporal context window management
- audiences: Multi-audience segment prediction
- noise: Sarcasm, spam, bot detection
"""

from .types import (
    ModalityEmbedding,
    NarrativeStateVector,
    TemporalState,
    AudienceSegment,
    SegmentPrediction,
    MultiAudiencePrediction,
    FusionConfig,
)

__all__ = [
    "ModalityEmbedding",
    "NarrativeStateVector",
    "TemporalState",
    "AudienceSegment",
    "SegmentPrediction",
    "MultiAudiencePrediction",
    "FusionConfig",
]
