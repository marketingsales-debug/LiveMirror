"""Shared type definitions for LiveMirror."""

from .platform import Platform, SignalType, RawSignal, ScoredSignal
from .agent import AgentRole, Stance, BehavioralFingerprint, AgentPersona
from .prediction import (
    PredictionStatus, ConfidenceLevel, NarrativeStage,
    Prediction, PredictionReport,
)

__all__ = [
    "Platform", "SignalType", "RawSignal", "ScoredSignal",
    "AgentRole", "Stance", "BehavioralFingerprint", "AgentPersona",
    "PredictionStatus", "ConfidenceLevel", "NarrativeStage",
    "Prediction", "PredictionReport",
]
