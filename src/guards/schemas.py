"""
Pydantic schemas for structured AI reasoning.
Ensures every agent output is valid, cite-able, and deterministic.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class Citation(BaseModel):
    """A specific reference to a source signal."""
    source_id: str = Field(..., description="The unique ID of the signal (from Crawl4AI/Redpanda)")
    quote: str = Field(..., description="The exact text or snippet being referenced")
    relevance_score: float = Field(..., ge=0.0, le=1.0)

class AgentThought(BaseModel):
    """The structured internal reasoning of an agent."""
    observation: str = Field(..., description="What the agent currently sees in the environment")
    logic: str = Field(..., description="Step-by-step reasoning process")
    citations: List[Citation] = Field(default_factory=list, description="Verifiable references to source signals")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Self-assessed confidence in this specific thought")

class AgentAction(BaseModel):
    """A concrete action the agent wants to take."""
    type: str = Field(..., description="Action type: READ_FILE, WRITE_FILE, RUN_COMMAND, SEARCH_WEB, COMPLETE")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")

class StructuredResponse(BaseModel):
    """The final structured output for a graph node."""
    thought: AgentThought
    action: Optional[AgentAction] = None
    next_step: str = Field(..., description="The next node to transition to in the LangGraph")

    @field_validator("next_step")
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        allowed = ["researcher", "coder", "analyst", "ema", "end"]
        if v.lower() not in allowed:
            raise ValueError(f"Invalid next_step: {v}. Must be one of {allowed}")
        return v.lower()
