"""
Context Window Manager — maintains bounded deque of narrative states.
Owner: Claude

Tracks temporal window of recent signals for trend analysis.
"""

from collections import deque
from typing import List, Optional
from datetime import datetime, timedelta

from ..types import NarrativeStateVector


class ContextWindowManager:
    """
    Maintains a bounded window of narrative states.
    
    Enables temporal context for trend detection and time-windowed retrieval.
    """
    
    def __init__(self, window_size: int = 50, time_window: Optional[timedelta] = None):
        """
        Initialize context window.
        
        Args:
            window_size: Max number of states to keep
            time_window: Optional time window (e.g., timedelta(hours=1))
        """
        self.window_size = window_size
        self.time_window = time_window
        self.states: deque = deque(maxlen=window_size)
    
    def add_state(self, state: NarrativeStateVector) -> None:
        """Add a new narrative state to the window."""
        self.states.append(state)
    
    def get_recent(self, num_states: Optional[int] = None) -> List[NarrativeStateVector]:
        """Get most recent N states."""
        if num_states is None:
            return list(self.states)
        return list(self.states)[-num_states:]
    
    def get_in_time_window(self, since: datetime) -> List[NarrativeStateVector]:
        """Get all states since a certain time."""
        if not self.time_window:
            return list(self.states)
        
        cutoff = datetime.now() - self.time_window
        return [s for s in self.states if s.timestamp >= cutoff]
    
    def get_by_platform(self, platform: str) -> List[NarrativeStateVector]:
        """Get all states from a specific platform."""
        return [s for s in self.states if s.platform == platform]
    
    def is_full(self) -> bool:
        """Check if window is at capacity."""
        return len(self.states) >= self.window_size
    
    def clear(self) -> None:
        """Clear all states."""
        self.states.clear()
