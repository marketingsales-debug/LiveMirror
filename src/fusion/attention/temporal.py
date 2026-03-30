"""
Temporal Transformer — models temporal dynamics (velocity, acceleration).
Owner: Claude

Uses sinusoidal positional encoding for time-based attention.
Outputs TemporalState with velocity and acceleration vectors.
"""

import numpy as np
from typing import List, Optional
from datetime import datetime

from ..types import TemporalState, NarrativeStateVector


class TemporalTransformer:
    """
    Models temporal sequences with positional encoding.
    
    Computes temporal derivatives (velocity, acceleration) from embedding sequences.
    """
    
    def __init__(self, embedding_dim: int = 384, max_seq_len: int = 50):
        """Initialize temporal transformer."""
        self.embedding_dim = embedding_dim
        self.max_seq_len = max_seq_len
        self.pos_encoding = self._create_positional_encoding(max_seq_len, embedding_dim)
    
    def _create_positional_encoding(self, max_len: int, d_model: int) -> np.ndarray:
        """Create sinusoidal positional encoding."""
        pos = np.arange(max_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        
        encoding = np.zeros((max_len, d_model))
        encoding[:, 0::2] = np.sin(pos * div_term)
        encoding[:, 1::2] = np.cos(pos * div_term)
        
        return encoding.astype(np.float32)
    
    def compute_temporal_state(
        self,
        states: List[NarrativeStateVector],
        current_timestamp: Optional[datetime] = None,
    ) -> Optional[TemporalState]:
        """
        Compute temporal dynamics from sequence of states.
        
        Args:
            states: Sequence of narrative states (oldest to newest)
            current_timestamp: Current time (default: now)
        
        Returns:
            TemporalState with velocity and acceleration
        """
        if len(states) < 2:
            return None
        
        # Get fused embeddings
        embeddings = [
            s.fused_embedding if s.fused_embedding is not None
            else np.zeros(self.embedding_dim, dtype=np.float32)
            for s in states
        ]
        
        # Apply positional encoding (oldest -> newest)
        max_idx = min(len(embeddings), self.max_seq_len)
        embedding_slice = embeddings[-max_idx:]
        encoded = []
        for i, embedding in enumerate(embedding_slice):
            enc = embedding + self.pos_encoding[i]
            encoded.append(enc)
        
        # Compute velocity (first derivative)
        velocity = self._compute_velocity(encoded)
        
        # Compute acceleration (second derivative)
        acceleration = self._compute_acceleration(encoded)
        
        # Compute momentum (trend strength)
        momentum = self._compute_momentum(velocity)
        
        return TemporalState(
            timestamp=current_timestamp or datetime.now(),
            embedding=embeddings[-1],  # Most recent embedding
            velocity=velocity,
            acceleration=acceleration,
            momentum=momentum,
        )
    
    def _compute_velocity(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """Compute velocity (embedding change over time)."""
        if len(embeddings) < 2:
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        # Average velocity across time steps
        velocities = []
        for i in range(1, len(embeddings)):
            v = embeddings[i] - embeddings[i - 1]
            velocities.append(v)
        
        avg_velocity = np.mean(velocities, axis=0)
        return avg_velocity.astype(np.float32)
    
    def _compute_acceleration(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """Compute acceleration (velocity change over time)."""
        if len(embeddings) < 3:
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        # Compute velocities
        velocities = [embeddings[i] - embeddings[i - 1] for i in range(1, len(embeddings))]
        
        # Compute acceleration
        accelerations = [velocities[i] - velocities[i - 1] for i in range(1, len(velocities))]
        
        avg_acceleration = np.mean(accelerations, axis=0)
        return avg_acceleration.astype(np.float32)
    
    def _compute_momentum(self, velocity: np.ndarray) -> float:
        """Compute momentum (magnitude of velocity trend)."""
        return float(np.linalg.norm(velocity))
