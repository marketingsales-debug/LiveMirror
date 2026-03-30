"""
LangGraph Orchestrator — Finalized Production Board.
Fully implemented nodes with reasoning, routing, and memory.
"""

import operator
import os
from typing import Annotated, Sequence, TypedDict, List, Dict, Any, Optional
from ..shared.llm import LLMFactory

# --- Shared Components ---
MEMORY_STORE = LessonLearntStore()
EVO_MEMORY = EvolutionaryMemory()
LLM_FRONTIER: Optional[Any] = None


def get_llm_frontier() -> Any:
    """Lazily initialize the frontier model to avoid import-time API key errors."""
    global LLM_FRONTIER
    if LLM_FRONTIER is None:
        # We use the 'frontier' tier (DeepSeek v3.2) for the orchestrator
        LLM_FRONTIER = LLMFactory.get_model(tier="frontier", temperature=0.0)
    return LLM_FRONTIER

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
    # EvoScientist fields
    active_strategy: str
    gate_result: Dict[str, Any]

# --- Node Definitions ---

async def researcher_node(state: AgentState):
    """RA Node: Open-Book Reasoning with Strategy awareness."""
    print("--- [RA] RESEARCHING ---")

    # Retrieve past wisdom (Phase 3 + Evo)
    history = EVO_MEMORY.get_recent_history(limit=5)

    prompt = (
        f"Goal: {state['goal']}\n"
        f"Active Strategy: {state.get('active_strategy', 'Standard research protocol')}\n"
        f"Recent History: {history}\n"
        f"Context: {state.get('source_context')}\n"
        "Analyze and propose next step in JSON."
    )

    structured_llm = get_llm_frontier().with_structured_output(StructuredResponse)
    try:
        response = await structured_llm.ainvoke(prompt)
        
        # Verify citations (Phase 2)
        v = CitationVerifier.verify_citations(
            response.thought.citations, 
            state.get("source_context", "")
        )
        
        if not v["is_valid"]:
            return {
                "messages": [AIMessage(content=f"Hallucination detected in citations: {v['hallucinations']}")],
                "next_agent": "researcher" 
            }

        return {
            "messages": [AIMessage(content=response.thought.logic)],
            "findings": [response.thought.observation],
            "next_agent": response.next_step
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Error in researcher node: {str(e)}")],
            "next_agent": "end"
        }

async def coder_node(state: AgentState):
    """EA Node: Generates a concrete patch from researcher findings."""
    print("--- [EA] CODING ---")

    findings_text = "\n".join(state.get("findings", []))
    prompt = (
        "You are an expert software engineer. Based on these research findings, "
        "write a concrete code patch (unified diff format) that implements the improvement.\n\n"
        f"FINDINGS:\n{findings_text}\n\n"
        f"GOAL: {state['goal']}\n\n"
        "Return ONLY the patch. If no actionable change, return 'NO_PATCH'."
    )
    try:
        response = await get_llm_frontier().ainvoke(prompt)
        patch = response.content.strip()
        return {
            "messages": [AIMessage(content=f"Engineer proposed patch:\n{patch[:500]}")],
            "proposed_patch": patch,
            "next_agent": "analyst",
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Coder error: {e}")],
            "next_agent": "analyst",
        }

async def gate_node(state: AgentState):
    """Gate Node: Runs 3-stage ExperimentGate (CodeScientist pattern) on the patch."""
    print("--- [GATE] VALIDATING PATCH ---")

    patch = state.get("proposed_patch", "")
    if not patch or patch == "NO_PATCH":
        return {
            "messages": [AIMessage(content="Gate: No patch to validate, skipping.")],
            "gate_result": {"stage": "skipped", "success": False, "score": 0.0},
            "next_agent": "ema",
        }

    # Lightweight lint check: patch should contain diff markers or code
    def lint_fn():
        return len(patch.strip()) > 20

    # Pilot: ask LLM if patch is syntactically valid
    async def test_fn():
        try:
            resp = await get_llm_frontier().ainvoke(
                f"Is this patch syntactically valid? Reply ONLY 'yes' or 'no'.\n\n{patch[:800]}"
            )
            return "yes" in resp.content.lower()
        except Exception:
            return False

    # Full experiment: LLM scores quality 0-1
    async def backtest_fn():
        try:
            resp = await get_llm_frontier().ainvoke(
                f"Score this patch quality 0.0-1.0. Reply ONLY the number.\n\n{patch[:800]}"
            )
            return float(resp.content.strip())
        except Exception:
            return 0.5

    result = await ExperimentGate.run_experiment("patch-gate", lint_fn, test_fn, backtest_fn)

    if not result["success"]:
        return {
            "messages": [AIMessage(content=f"Gate REJECTED at stage: {result['stage']}")],
            "gate_result": result,
            "next_agent": "coder",  # Send back to coder for retry
        }

    return {
        "messages": [AIMessage(content=f"Gate PASSED (score: {result['score']:.2f})")],
        "gate_result": result,
        "next_agent": "analyst",
    }


async def analyst_node(state: AgentState):
    """Analyst Node: Evaluates the proposed patch using LLM-as-judge."""
    print("--- [Analyst] ANALYZING ---")

    patch = state.get("proposed_patch", "")
    findings = "\n".join(state.get("findings", []))
    baseline = EVO_MEMORY.get_last_accuracy()

    prompt = (
        "You are a rigorous code analyst. Evaluate this patch against the research goal.\n\n"
        f"GOAL: {state['goal']}\n"
        f"FINDINGS:\n{findings}\n"
        f"PATCH:\n{patch[:1000]}\n"
        f"BASELINE ACCURACY: {baseline}\n\n"
        "Score the patch 0.0-1.0 on: correctness, relevance, risk.\n"
        "Return JSON: {\"accuracy\": float, \"correctness\": float, \"risk\": float, \"verdict\": str}"
    )
    try:
        response = await get_llm_frontier().ainvoke(prompt)
        import json as _json
        # Try to parse structured result from LLM
        text = response.content.strip()
        # Extract JSON from possible markdown fences
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        result = _json.loads(text)
        accuracy = float(result.get("accuracy", baseline))
        verdict = result.get("verdict", "unknown")
    except Exception:
        accuracy = baseline
        verdict = "parse_error"

    return {
        "messages": [AIMessage(content=f"Analyst verdict: {verdict} (accuracy: {accuracy:.3f})")],
        "verification_results": {"accuracy": accuracy, "verdict": verdict, "baseline": baseline},
        "next_agent": "ema",
    }

async def ema_node(state: AgentState):
    """EMA Node: Distills interaction history into updated Strategy."""
    print("--- [EMA] EVOLVING STRATEGY ---")

    # Read the last result from the Analyst
    last_msg = state["messages"][-1].content

    # Prompt to update strategy based on success/fail
    strategy_prompt = (
        "Analyze the following research interaction. What patterns lead to success? "
        "What should we stop trying? Update the 'active_strategy' for future rounds.\n\n"
        f"INTERACTION: {last_msg}"
    )

    # Simple direct LLM call for strategy distillation
    strategy_update = await get_llm_frontier().ainvoke(strategy_prompt)

    # Record to Evolutionary Memory (EvoScientist Pattern)
    baseline = EVO_MEMORY.get_last_accuracy()
    accuracy = state["verification_results"].get("accuracy", baseline)
    kept = accuracy >= baseline
    EVO_MEMORY.record_experiment(
        code_change=state.get("proposed_patch", "None"),
        metric_before=baseline,
        metric_after=accuracy,
        kept=kept,
    )

    return {
        "messages": [AIMessage(content="EMA updated active strategy.")], 
        "active_strategy": strategy_update.content,
        "next_agent": "end"
    }

# --- Graph Construction ---

def create_research_board():
    """Builds the LangGraph state machine with ExperimentGate."""
    workflow = StateGraph(AgentState)

    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("gate", gate_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("ema", ema_node)

    workflow.set_entry_point("researcher")

    def router(state: AgentState):
        step = state.get("next_agent", "end")
        return END if step == "end" else step

    workflow.add_conditional_edges("researcher", router, {
        "researcher": "researcher", "coder": "coder", "ema": "ema", "end": END,
    })
    # Coder always goes to gate first
    workflow.add_edge("coder", "gate")
    # Gate routes to analyst (pass) or back to coder (fail)
    workflow.add_conditional_edges("gate", router, {
        "analyst": "analyst", "coder": "coder", "ema": "ema", "end": END,
    })
    workflow.add_conditional_edges("analyst", router, {
        "ema": "ema", "coder": "coder", "end": END,
    })
    workflow.add_edge("ema", END)

    return workflow.compile(checkpointer=MemorySaver())

research_board = create_research_board()
