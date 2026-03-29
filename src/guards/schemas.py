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

class RubricJudge:
    """Grades predictions using hierarchical rubrics (PaperBench Pattern)."""
    
    RUBRIC = {
        "logic_quality": {
            "has_direction": 0.2, # Direction must be up/down/neutral
            "has_evidence": 0.3,  # Must cite at least 2 sources
            "source_validity": 0.3, # Sources must exist in context
            "calibration": 0.2,    # Confidence must be between 0.1 and 0.99
        }
    }

    @staticmethod
    def grade_response(response: StructuredResponse, context_verified: bool) -> float:
        """Calculate a score from 0.0 to 1.0 based on the rubric."""
        score = 0.0
        checks = RubricJudge.RUBRIC["logic_quality"]
        
        # 1. Has direction
        if response.thought.logic: # Simplified check
            score += checks["has_direction"]
            
        # 2. Has evidence
        if len(response.thought.citations) >= 2:
            score += checks["has_evidence"]
            
        # 3. Source validity (passed from CitationVerifier)
        if context_verified:
            score += checks["source_validity"]
            
        # 4. Calibration
        if 0.1 <= response.thought.confidence <= 0.99:
            score += checks["calibration"]
            
        return round(score, 2)
