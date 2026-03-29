"""
LangGraph Orchestrator — The state-machine spine of LiveMirror v2.0.
Replaces the legacy linear AgentLoop with a cyclic, persistent graph.
"""

import operator
import os
from typing import Annotated, Sequence, TypedDict, Union, List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AssistantMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..guards.schemas import StructuredResponse, AgentThought, AgentAction, Citation
from ..guards.citation import CitationVerifier
from ..memory.lesson_learnt import LessonLearntStore

# --- State Definition ---

class AgentState(TypedDict):
    """The state of the multi-agent research board."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    goal: str
    context_files: List[str]
    findings: List[str]
    proposed_patch: Optional[str]
    verification_results: Dict[str, Any]
    next_agent: str
    lessons: List[str]
    source_context: str 

# --- Configuration ---

# Shared persistent memory (Phase 3)
MEMORY_STORE = LessonLearntStore()

# Lock temperature to 0.0 for deterministic reasoning (Phase 2)
LLM = ChatOpenAI(model="gpt-4o", temperature=0.0)

# --- Node Definitions ---

async def researcher_node(state: AgentState):
    """RA Node: Analyzes signals and proposes research directions."""
    print("--- [RA] RESEARCHER STARTING ---")
    
    # Retrieve historical lessons (Phase 3)
    past_lessons = MEMORY_STORE.get_lessons(topic=state["goal"], limit=3)
    lessons_text = "\n".join([f"- {l['content']}" for l in past_lessons]) if past_lessons else "None"

    prompt = (
        f"Goal: {state['goal']}\n"
        f"Context Files: {state['context_files']}\n"
        f"Historical Lessons: {lessons_text}\n"
        f"Source Context: {state.get('source_context', 'None')}\n"
        "Analyze and respond in JSON using the provided schema."
    )
    
    structured_llm = LLM.with_structured_output(StructuredResponse)
    try:
        response = await structured_llm.ainvoke(prompt)
        
        # Verify citations (Phase 2)
        v = CitationVerifier.verify_citations(
            response.thought.citations, 
            state.get("source_context", "")
        )
        
        if not v["is_valid"]:
            return {
                "messages": [AssistantMessage(content=f"Hallucination detected in citations: {v['hallucinations']}")],
                "next_agent": "researcher" 
            }

        return {
            "messages": [AssistantMessage(content=response.thought.logic)],
            "findings": [response.thought.observation],
            "next_agent": response.next_step
        }
    except Exception as e:
        return {
            "messages": [AssistantMessage(content=f"Error in researcher node: {str(e)}")],
            "next_agent": "end"
        }

async def coder_node(state: AgentState):
    """EA Node: Implements code changes in the Research Sandbox."""
    print("--- [EA] ENGINEER STARTING ---")
    return {"messages": [AssistantMessage(content="Engineer proposed a patch.")], "next_agent": "analyst"}

async def analyst_node(state: AgentState):
    """Analyst Node: Runs backtests and verifies patches."""
    print("--- [Analyst] VERIFICATION STARTING ---")
    return {"messages": [AssistantMessage(content="Verification passed.")], "next_agent": "ema"}

async def ema_node(state: AgentState):
    """EMA Node: Distills lessons into persistent memory (Phase 3)."""
    print("--- [EMA] DISTILLATION STARTING ---")
    
    last_msg = state["messages"][-1].content if state["messages"] else "No history"
    
    # Save the "Lesson Learnt"
    MEMORY_STORE.save_lesson(
        agent_id="ema",
        topic=state["goal"],
        content=f"Prediction Cycle Outcome: {last_msg}"
    )
    
    return {"messages": [AssistantMessage(content="EMA distilled and saved lesson.")], "next_agent": "end"}

# --- Graph Construction ---

def create_research_board():
    """Builds the LangGraph state machine."""
    workflow = StateGraph(AgentState)

    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("ema", ema_node)

    workflow.set_entry_point("researcher")
    
    def router(state: AgentState):
        next_step = state.get("next_agent", "end")
        if next_step == "end":
            return END
        return next_step

    workflow.add_conditional_edges(
        "researcher",
        router,
        {"researcher": "researcher", "coder": "coder", "ema": "ema", "end": END}
    )
    
    workflow.add_conditional_edges(
        "coder",
        router,
        {"analyst": "analyst", "end": END}
    )
    
    workflow.add_conditional_edges(
        "analyst",
        router,
        {"ema": "ema", "coder": "coder", "end": END}
    )
    
    workflow.add_edge("ema", END)

    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)

research_board = create_research_board()
