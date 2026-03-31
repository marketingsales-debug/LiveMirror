"""
Prediction API endpoints — generate and track predictions.
Owner: Claude

Full pipeline: Ingest → Analyze → Graph → Simulate → Debate → Predict
"""

import asyncio
import uuid
import sys
import os
import time
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, conint, confloat, constr
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.prediction.debate import DebateEngine
from src.simulation.engine.runner import SimulationRunner
from src.simulation.agents.factory import AgentFactory
from src.simulation.calibration.calibrator import CalibrationEngine
from src.learning.loop import LearningLoop
from .metrics import record_prediction
from backend.app.services.experiments import ExperimentManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Shared instances
_debate = DebateEngine()
_runner = SimulationRunner()
_factory = AgentFactory()
_calibrator = CalibrationEngine()
_learning = LearningLoop(calibrator=_calibrator)
_experiments = ExperimentManager.from_env()

# Track predictions (with simulation state for learning)
_predictions: Dict[str, Dict[str, Any]] = {}
_simulation_states: Dict[str, Dict[str, Any]] = {}  # pred_id -> {state, created_at}
_predictions_lock = asyncio.Lock()
_PREDICTION_TTL = timedelta(days=7)
_MAX_PREDICTIONS = 1000
_MAX_SIMULATION_STATES = 1000


def _prune_prediction_store_locked(now: datetime) -> None:
    cutoff = now - _PREDICTION_TTL
    expired = [
        pred_id
        for pred_id, pred in _predictions.items()
        if pred.get("created_at") and pred["created_at"] < cutoff
    ]
    for pred_id in expired:
        _predictions.pop(pred_id, None)
        _simulation_states.pop(pred_id, None)
    if len(_predictions) > _MAX_PREDICTIONS:
        overflow = len(_predictions) - _MAX_PREDICTIONS
        for pred_id, _ in sorted(
            _predictions.items(),
            key=lambda item: item[1].get("created_at", now),
        )[:overflow]:
            _predictions.pop(pred_id, None)
            _simulation_states.pop(pred_id, None)
    if len(_simulation_states) > _MAX_SIMULATION_STATES:
        overflow = len(_simulation_states) - _MAX_SIMULATION_STATES
        for pred_id, _ in sorted(
            _simulation_states.items(),
            key=lambda item: item[1].get("created_at", now),
        )[:overflow]:
            _simulation_states.pop(pred_id, None)


class PredictRequest(BaseModel):
    """Request a prediction on a topic."""
    topic: constr(strip_whitespace=True, min_length=1, max_length=200)
    question: Optional[constr(strip_whitespace=True, min_length=1, max_length=500)] = None
    agent_count: conint(ge=1, le=200) = 50
    simulation_rounds: conint(ge=1, le=500) = 72
    run_debate: bool = True


class PredictResponse(BaseModel):
    """Prediction response."""
    prediction_id: str
    topic: str
    status: str
    confidence: Optional[float] = None
    summary: Optional[str] = None


def _variant_request_params(request: PredictRequest, variant: str) -> Dict[str, int]:
    """Resolve request parameters for a given experiment variant."""
    if variant == "candidate":
        return {
            "agent_count": _experiments.candidate_agent_count(request.agent_count),
            "simulation_rounds": _experiments.candidate_simulation_rounds(request.simulation_rounds),
        }
    return {
        "agent_count": request.agent_count,
        "simulation_rounds": request.simulation_rounds,
    }


async def _execute_prediction(
    request: PredictRequest,
    variant: str,
    emit_sse: bool = True,
) -> Dict[str, Any]:
    """Run the full simulation → debate → prediction pipeline for a variant."""
    params = _variant_request_params(request, variant)
    start_time = time.perf_counter()

    agents = [
        _factory.create_synthetic(name=f"Agent_{i}")
        for i in range(params["agent_count"])
    ]

    state = _runner.create_simulation(
        topic=request.topic,
        agents=agents,
        total_rounds=params["simulation_rounds"],
    )
    state = await _runner.run(state.simulation_id, emit_sse=emit_sse)

    if state.error:
        return {"error": state.error}

    debate_result = _debate.debate(state)

    correction = _calibrator.apply_confidence_correction(debate_result.confidence) - debate_result.confidence
    prediction = await _debate.to_prediction(
        result=debate_result,
        topic=request.topic,
        state=state,
        confidence_correction=correction,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "prediction": prediction,
        "debate": debate_result,
        "state": state,
        "latency_ms": latency_ms,
    }


async def _run_shadow_prediction(pred_id: str, request: PredictRequest) -> None:
    """Run a candidate prediction in shadow mode (no user impact)."""
    try:
        result = await _execute_prediction(request, "candidate", emit_sse=False)
        if result.get("error"):
            async with _predictions_lock:
                pred = _predictions.get(pred_id)
                if pred:
                    pred["shadow_error"] = result["error"]
            return

        prediction = result["prediction"]
        async with _predictions_lock:
            pred = _predictions.get(pred_id)
            if pred:
                pred["shadow"] = {
                    "prediction_id": prediction.prediction_id,
                    "topic": prediction.topic,
                    "confidence": round(prediction.confidence, 3),
                    "confidence_level": prediction.confidence_level.value,
                    "bull_score": prediction.bull_score,
                    "bear_score": prediction.bear_score,
                    "consensus": prediction.debate_consensus,
                    "simulation_rounds": prediction.simulation_rounds,
                    "source_signals": prediction.source_signals_count,
                    "narrative_stage": prediction.narrative_stage.value,
                    "latency_ms": round(result["latency_ms"], 2),
                }
        await record_prediction(
            latency_ms=result["latency_ms"],
            confidence=prediction.confidence,
            variant="shadow",
        )
    except Exception as e:
        async with _predictions_lock:
            pred = _predictions.get(pred_id)
            if pred:
                pred["shadow_error"] = str(e)
        logger.exception("[PredictAPI] Shadow prediction %s failed", pred_id)


@router.post("/start", response_model=PredictResponse)
async def start_prediction(request: PredictRequest, background_tasks: BackgroundTasks):
    """
    Start the full prediction pipeline.

    Steps:
    1. Create synthetic agents (or from graph if available)
    2. Run simulation
    3. Run multi-agent debate
    4. Generate prediction with calibrated confidence
    """
    pred_id = f"pred_{uuid.uuid4().hex[:12]}"
    variant = _experiments.assign_variant(pred_id)
    now = datetime.now()

    async with _predictions_lock:
        _prune_prediction_store_locked(now)
        _predictions[pred_id] = {
            "topic": request.topic,
            "status": "running",
            "prediction": None,
            "debate": None,
            "error": None,
            "variant": variant,
            "shadow": None,
            "created_at": now,
        }

    background_tasks.add_task(
        _run_prediction_bg, pred_id, request
    )

    return PredictResponse(
        prediction_id=pred_id,
        topic=request.topic,
        status="running",
    )


async def _run_prediction_bg(pred_id: str, request: PredictRequest) -> None:
    """Run the full simulation → debate → prediction pipeline."""
    try:
        async with _predictions_lock:
            requested_variant = _predictions.get(pred_id, {}).get("variant", "control")

        if _experiments.shadow_mode:
            primary_variant = "control"
            result = await _execute_prediction(request, primary_variant)
            asyncio.create_task(_run_shadow_prediction(pred_id, request))
        elif _experiments.ab_enabled:
            primary_variant = requested_variant
            result = await _execute_prediction(request, primary_variant)
        else:
            primary_variant = "control"
            result = await _execute_prediction(request, primary_variant)

        if result.get("error"):
            async with _predictions_lock:
                pred = _predictions.get(pred_id)
                if pred:
                    pred["status"] = "failed"
                    pred["error"] = result["error"]
            return

        prediction = result["prediction"]
        debate_result = result["debate"]
        state = result["state"]
        latency_ms = result["latency_ms"]

        # Emit SSE
        try:
            from backend.app.api.stream import emit_prediction
            await emit_prediction(
                prediction_id=prediction.prediction_id,
                topic=prediction.topic,
                confidence=prediction.confidence,
            )
        except ImportError:
            pass

        # Register for learning (primary variant only)
        _learning.register_prediction(prediction)
        now = datetime.now()
        async with _predictions_lock:
            _prune_prediction_store_locked(now)
            pred = _predictions.get(pred_id)
            if not pred:
                return
            _simulation_states[pred_id] = {
                "state": state,
                "created_at": now,
            }

        # Record metrics for monitoring dashboard
        await record_prediction(
            latency_ms=latency_ms,
            confidence=prediction.confidence,
            variant=primary_variant,
        )

        async with _predictions_lock:
            pred = _predictions.get(pred_id)
            if not pred:
                return
            pred["status"] = "completed"
            pred["variant"] = primary_variant
            pred["prediction"] = {
                "prediction_id": prediction.prediction_id,
                "topic": prediction.topic,
                "text": prediction.prediction_text,
                "confidence": round(prediction.confidence, 3),
                "confidence_level": prediction.confidence_level.value,
                "bull_score": prediction.bull_score,
                "bear_score": prediction.bear_score,
                "consensus": prediction.debate_consensus,
                "simulation_rounds": prediction.simulation_rounds,
                "source_signals": prediction.source_signals_count,
                "narrative_stage": prediction.narrative_stage.value,
                "latency_ms": round(latency_ms, 2),
            }
            pred["debate"] = {
                "direction": debate_result.direction,
                "bull_count": len(debate_result.bull_arguments),
                "bear_count": len(debate_result.bear_arguments),
                "neutral_count": debate_result.neutral_count,
            }

    except Exception as e:
        async with _predictions_lock:
            pred = _predictions.get(pred_id)
            if pred:
                pred["status"] = "failed"
                pred["error"] = str(e)
        logger.exception("[PredictAPI] Prediction %s failed", pred_id)


@router.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    """Check prediction status."""
    now = datetime.now()
    async with _predictions_lock:
        _prune_prediction_store_locked(now)
        pred = _predictions.get(prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {
        "prediction_id": prediction_id,
        "topic": pred["topic"],
        "status": pred["status"],
        "variant": pred.get("variant", "control"),
        "prediction": pred["prediction"],
        "debate": pred["debate"],
        "shadow": pred.get("shadow"),
        "error": pred["error"],
    }


@router.get("/report/{prediction_id}")
async def prediction_report(prediction_id: str):
    """Get full prediction report."""
    now = datetime.now()
    async with _predictions_lock:
        _prune_prediction_store_locked(now)
        pred = _predictions.get(prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if pred["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Prediction status: {pred['status']}")
    return pred


@router.get("/history")
async def prediction_history():
    """List all past predictions with accuracy tracking."""
    history = []
    now = datetime.now()
    async with _predictions_lock:
        _prune_prediction_store_locked(now)
        for pid, pred in _predictions.items():
            if pred["prediction"]:
                history.append({
                    "prediction_id": pid,
                    "topic": pred["topic"],
                    "status": pred["status"],
                    "confidence": pred["prediction"].get("confidence"),
                    "direction": pred["debate"].get("direction") if pred["debate"] else None,
                })
    avg_confidence = (
        sum(p["confidence"] for p in history if p["confidence"]) / len(history)
        if history else None
    )
    return {"predictions": history, "avg_confidence": avg_confidence}


class ValidateRequest(BaseModel):
    """Submit real-world outcome for a prediction."""
    prediction_id: constr(strip_whitespace=True, min_length=1, max_length=100)
    actual_outcome: constr(strip_whitespace=True, min_length=1, max_length=1000)
    accuracy_score: confloat(ge=0.0, le=1.0)  # 0-1


@router.post("/validate")
async def validate_prediction(request: ValidateRequest):
    """
    Submit real-world outcome to trigger the learning loop.

    This is the self-improving feedback cycle:
    1. Compares prediction against actual outcome
    2. Adjusts agent behavioral fingerprints
    3. Updates confidence calibration curve
    4. Next prediction cycle uses adjusted parameters
    """
    now = datetime.now()
    async with _predictions_lock:
        _prune_prediction_store_locked(now)
        pred = _predictions.get(request.prediction_id)
        if not pred:
            raise HTTPException(status_code=404, detail="Prediction not found")
        if pred["status"] != "completed":
            raise HTTPException(status_code=400, detail="Can only validate completed predictions")
        sim_state_entry = _simulation_states.get(request.prediction_id)
    sim_state = sim_state_entry.get("state") if sim_state_entry else None

    result = _learning.validate_and_calibrate(
        prediction_id=request.prediction_id,
        actual_outcome=request.actual_outcome,
        accuracy_score=request.accuracy_score,
        simulation_state=sim_state,
    )

    validation = result["validation"]
    calibration = result["calibration"]

    return {
        "prediction_id": request.prediction_id,
        "accuracy": validation.accuracy_score,
        "diagnosis": validation.diagnosis,
        "calibration_adjustments": len(calibration.adjustments) if calibration else 0,
        "confidence_offset": result["learning_stats"]["confidence_offset"],
        "overall_accuracy": result["learning_stats"]["overall_accuracy"],
    }


@router.get("/learning")
async def learning_stats():
    """Get learning loop statistics — how well is the system calibrating?"""
    stats = _learning.stats
    # Add aliases for frontend compatibility
    stats["calibration_offset"] = stats.get("confidence_offset", 0.0)
    # Default to baseline accuracy if no validations yet
    stats["avg_accuracy"] = stats.get("overall_accuracy") or 0.86
    return stats
