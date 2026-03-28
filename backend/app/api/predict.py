"""
Prediction API endpoints — generate and track predictions.
Owner: Claude

Full pipeline: Ingest → Analyze → Graph → Simulate → Debate → Predict
"""

import asyncio
import uuid
import sys
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.prediction.debate import DebateEngine
from src.simulation.engine.runner import SimulationRunner
from src.simulation.agents.factory import AgentFactory
from src.simulation.calibration.calibrator import CalibrationEngine
from src.learning.loop import LearningLoop
from src.shared.types import Prediction, PredictionStatus

router = APIRouter()

# Shared instances
_debate = DebateEngine()
_runner = SimulationRunner()
_factory = AgentFactory()
_calibrator = CalibrationEngine()
_learning = LearningLoop(calibrator=_calibrator)

# Track predictions (with simulation state for learning)
_predictions: Dict[str, Dict[str, Any]] = {}
_simulation_states: Dict[str, Any] = {}  # pred_id -> SimulationState


class PredictRequest(BaseModel):
    """Request a prediction on a topic."""
    topic: str
    question: Optional[str] = None
    agent_count: int = 50
    simulation_rounds: int = 72
    run_debate: bool = True


class PredictResponse(BaseModel):
    """Prediction response."""
    prediction_id: str
    topic: str
    status: str
    confidence: Optional[float] = None
    summary: Optional[str] = None


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

    _predictions[pred_id] = {
        "topic": request.topic,
        "status": "running",
        "prediction": None,
        "debate": None,
        "error": None,
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
        # 1. Create agents (synthetic for now — graph integration via ingest API)
        agents = [
            _factory.create_synthetic(name=f"Agent_{i}")
            for i in range(request.agent_count)
        ]

        # 2. Run simulation
        state = _runner.create_simulation(
            topic=request.topic,
            agents=agents,
            total_rounds=request.simulation_rounds,
        )
        state = await _runner.run(state.simulation_id, emit_sse=True)

        if state.error:
            _predictions[pred_id]["status"] = "failed"
            _predictions[pred_id]["error"] = state.error
            return

        # 3. Run debate
        debate_result = _debate.debate(state)

        # 4. Generate prediction with calibration
        correction = _calibrator.apply_confidence_correction(debate_result.confidence) - debate_result.confidence
        prediction = _debate.to_prediction(
            result=debate_result,
            topic=request.topic,
            state=state,
            confidence_correction=correction,
        )

        # 5. Emit SSE
        try:
            from backend.app.api.stream import emit_prediction
            await emit_prediction(
                prediction_id=prediction.prediction_id,
                topic=prediction.topic,
                confidence=prediction.confidence,
            )
        except ImportError:
            pass

        # 6. Register for learning
        _learning.register_prediction(prediction)
        _simulation_states[pred_id] = state

        _predictions[pred_id]["status"] = "completed"
        _predictions[pred_id]["prediction"] = {
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
        }
        _predictions[pred_id]["debate"] = {
            "direction": debate_result.direction,
            "bull_count": len(debate_result.bull_arguments),
            "bear_count": len(debate_result.bear_arguments),
            "neutral_count": debate_result.neutral_count,
        }

    except Exception as e:
        _predictions[pred_id]["status"] = "failed"
        _predictions[pred_id]["error"] = str(e)
        print(f"[PredictAPI] Prediction {pred_id} failed: {e}")


@router.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    """Check prediction status."""
    pred = _predictions.get(prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {
        "prediction_id": prediction_id,
        "topic": pred["topic"],
        "status": pred["status"],
        "prediction": pred["prediction"],
        "debate": pred["debate"],
        "error": pred["error"],
    }


@router.get("/report/{prediction_id}")
async def prediction_report(prediction_id: str):
    """Get full prediction report."""
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
    prediction_id: str
    actual_outcome: str
    accuracy_score: float  # 0-1


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
    pred = _predictions.get(request.prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if pred["status"] != "completed":
        raise HTTPException(status_code=400, detail="Can only validate completed predictions")

    sim_state = _simulation_states.get(request.prediction_id)

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
    return _learning.stats
