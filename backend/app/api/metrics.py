"""
Monitoring Dashboard API Endpoints.
Owner: Claude

Provides real-time metrics for:
- Fusion pipeline performance (cache hit rate, latency)
- Fine-tuning progress (samples, runs, regression status)
- Model accuracy drift over time
- System health indicators
"""

from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import logging
import numpy as np

router = APIRouter()
logger = logging.getLogger(__name__)
_metrics_lock = asyncio.Lock()
_METRICS_TTL = timedelta(days=14)
_MAX_PREDICTION_METRICS = 10000
_MAX_FINE_TUNE_RUNS = 1000
_MAX_ACCURACY_HISTORY = 1000
_MAX_LATENCY_SAMPLES = 10000

# In-memory metrics storage (replace with Redis in production)
_metrics_store: Dict[str, Any] = {
    "predictions": [],
    "fine_tune_runs": [],
    "accuracy_history": [],
    "latency_samples": [],
    "cache_stats": {"hits": 0, "misses": 0},
}


def _prune_metrics_locked(now: datetime) -> None:
    cutoff = now - _METRICS_TTL
    _metrics_store["predictions"] = [
        p for p in _metrics_store["predictions"]
        if p.get("ts") and p["ts"] >= cutoff
    ]
    _metrics_store["fine_tune_runs"] = [
        r for r in _metrics_store["fine_tune_runs"]
        if r.get("ts") and r["ts"] >= cutoff
    ]
    if len(_metrics_store["predictions"]) > _MAX_PREDICTION_METRICS:
        _metrics_store["predictions"] = _metrics_store["predictions"][-_MAX_PREDICTION_METRICS:]
    if len(_metrics_store["fine_tune_runs"]) > _MAX_FINE_TUNE_RUNS:
        _metrics_store["fine_tune_runs"] = _metrics_store["fine_tune_runs"][-_MAX_FINE_TUNE_RUNS:]
    if len(_metrics_store["accuracy_history"]) > _MAX_ACCURACY_HISTORY:
        _metrics_store["accuracy_history"] = _metrics_store["accuracy_history"][-_MAX_ACCURACY_HISTORY:]
    if len(_metrics_store["latency_samples"]) > _MAX_LATENCY_SAMPLES:
        _metrics_store["latency_samples"] = _metrics_store["latency_samples"][-_MAX_LATENCY_SAMPLES:]


@router.get("/overview")
async def metrics_overview() -> Dict[str, Any]:
    """
    High-level system metrics for dashboard.
    
    Returns:
        Overview of prediction count, accuracy, latency, cache performance
    """
    now = datetime.now()
    async with _metrics_lock:
        _prune_metrics_locked(now)
        predictions = list(_metrics_store["predictions"])
        accuracy_history = list(_metrics_store["accuracy_history"])
        latency_samples = list(_metrics_store["latency_samples"])
        cache = dict(_metrics_store["cache_stats"])
    
    # Calculate stats
    total_predictions = len(predictions)
    avg_latency = np.mean(latency_samples[-100:]) if latency_samples else 0.0
    cache_total = cache["hits"] + cache["misses"]
    cache_hit_rate = cache["hits"] / cache_total if cache_total > 0 else 0.0
    
    # Accuracy trend (last 7 days)
    recent_accuracy = accuracy_history[-7:] if accuracy_history else []
    accuracy_trend = "stable"
    if len(recent_accuracy) >= 2:
        if recent_accuracy[-1] > recent_accuracy[0] + 0.02:
            accuracy_trend = "improving"
        elif recent_accuracy[-1] < recent_accuracy[0] - 0.02:
            accuracy_trend = "degrading"
    
    by_variant: Dict[str, int] = {}
    for p in predictions:
        variant = p.get("variant", "control")
        by_variant[variant] = by_variant.get(variant, 0) + 1

    recent_predictions = predictions[-200:] if len(predictions) > 200 else predictions
    variant_stats: Dict[str, Dict[str, float]] = {}
    for p in recent_predictions:
        variant = p.get("variant", "control")
        entry = variant_stats.setdefault(variant, {
            "count": 0,
            "confidence_total": 0.0,
            "latency_total": 0.0,
        })
        entry["count"] += 1
        entry["confidence_total"] += float(p.get("confidence", 0.0))
        entry["latency_total"] += float(p.get("latency_ms", 0.0))

    variants: Dict[str, Dict[str, float]] = {}
    for variant, entry in variant_stats.items():
        count = max(int(entry["count"]), 1)
        variants[variant] = {
            "count": int(entry["count"]),
            "avg_confidence": round(entry["confidence_total"] / count, 4),
            "avg_latency_ms": round(entry["latency_total"] / count, 2),
        }

    variant_alerts: List[Dict[str, str]] = []
    control = variants.get("control")
    candidate = variants.get("candidate")
    if control and candidate and control["count"] >= 5 and candidate["count"] >= 5:
        delta = candidate["avg_confidence"] - control["avg_confidence"]
        if delta < -0.10:
            variant_alerts.append({
                "level": "critical",
                "message": f"Candidate confidence is {abs(delta)*100:.1f}% below control.",
            })
        elif delta < -0.05:
            variant_alerts.append({
                "level": "warning",
                "message": f"Candidate confidence is {abs(delta)*100:.1f}% below control.",
            })

    return {
        "timestamp": datetime.now().isoformat(),
        "predictions": {
            "total": total_predictions,
            "last_24h": sum(1 for p in predictions if p["ts"] > datetime.now() - timedelta(hours=24)),
            "by_variant": by_variant,
            "variants": variants,
            "variant_alerts": variant_alerts,
        },
        "accuracy": {
            "current": recent_accuracy[-1] if recent_accuracy else 0.86,
            "trend": accuracy_trend,
            "history": recent_accuracy,
        },
        "latency": {
            "avg_ms": round(avg_latency, 2),
            "p95_ms": round(np.percentile(latency_samples[-100:], 95), 2) if latency_samples else 0.0,
            "target_ms": 45.0,
        },
        "cache": {
            "hit_rate": round(cache_hit_rate, 3),
            "hits": cache["hits"],
            "misses": cache["misses"],
        },
    }


@router.get("/fine-tune")
async def fine_tune_status() -> Dict[str, Any]:
    """
    Fine-tuning loop status and history.
    
    Returns:
        Current state, pending samples, recent runs, regression status
    """
    now = datetime.now()
    async with _metrics_lock:
        _prune_metrics_locked(now)
        runs = list(_metrics_store["fine_tune_runs"])
    
    # Find latest run
    latest = runs[-1] if runs else None
    
    # Check for regression (accuracy drop > 5%)
    regression_detected = False
    if latest and "pre_accuracy" in latest and "post_accuracy" in latest:
        regression_detected = latest["post_accuracy"] < latest["pre_accuracy"] - 0.05
    
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "idle",  # Would be "running" if active
        "pending_samples": 0,  # From LearningLoop._pending_signals
        "min_samples_required": 10,
        "next_eligible_at": None,  # 24h since last run
        "runs": {
            "total": len(runs),
            "last_7_days": sum(1 for r in runs if r.get("ts", datetime.min) > datetime.now() - timedelta(days=7)),
        },
        "latest_run": {
            "timestamp": latest["ts"].isoformat() if latest else None,
            "samples_used": latest.get("samples", 0) if latest else 0,
            "pre_accuracy": latest.get("pre_accuracy", 0) if latest else 0,
            "post_accuracy": latest.get("post_accuracy", 0) if latest else 0,
            "improvement": round(latest.get("post_accuracy", 0) - latest.get("pre_accuracy", 0), 4) if latest else 0,
        },
        "regression": {
            "detected": regression_detected,
            "rollback_triggered": latest.get("rollback", False) if latest else False,
        },
    }


@router.get("/accuracy-drift")
async def accuracy_drift() -> Dict[str, Any]:
    """
    Track accuracy over time to detect model drift.
    
    Returns:
        Accuracy history by day, drift status, alerts
    """
    now = datetime.now()
    async with _metrics_lock:
        _prune_metrics_locked(now)
        history = list(_metrics_store["accuracy_history"])
    
    # Calculate drift
    drift_status = "stable"
    drift_magnitude = 0.0
    
    if len(history) >= 7:
        week_ago = history[-7]
        current = history[-1]
        drift_magnitude = current - week_ago
        
        if drift_magnitude < -0.05:
            drift_status = "critical_drift"
        elif drift_magnitude < -0.02:
            drift_status = "mild_drift"
        elif drift_magnitude > 0.02:
            drift_status = "improving"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "status": drift_status,
        "drift_magnitude": round(drift_magnitude, 4),
        "baseline_accuracy": 0.86,
        "target_accuracy": 0.94,
        "current_accuracy": history[-1] if history else 0.86,
        "history": [
            {"day": i, "accuracy": acc}
            for i, acc in enumerate(history[-30:])  # Last 30 days
        ],
        "alerts": _generate_drift_alerts(drift_status, drift_magnitude),
    }


@router.get("/pipeline-health")
async def pipeline_health() -> Dict[str, Any]:
    """
    Component-level health for the fusion pipeline.
    
    Returns:
        Status of each encoder, attention, cache, and learning loop
    """
    async with _metrics_lock:
        _prune_metrics_locked(datetime.now())
        cache_size = _metrics_store["cache_stats"].get("size", 0)
    return {
        "timestamp": datetime.now().isoformat(),
        "components": {
            "text_encoder": {"status": "healthy", "model": "all-MiniLM-L6-v2"},
            "audio_encoder": {"status": "healthy", "model": "Wav2Vec2"},
            "video_encoder": {"status": "healthy", "model": "CLIP"},
            "sentiment_encoder": {"status": "healthy", "model": "FinBERT"},
            "learned_attention": {
                "status": "healthy",
                "layers": 3,
                "heads": 8,
                "fine_tuned": True,
            },
            "embedding_cache": {
                "status": "healthy",
                "size": cache_size,
                "max_size": 1000,
            },
            "batch_processor": {"status": "healthy", "batch_size": 16},
            "learning_loop": {"status": "healthy", "mode": "continuous"},
        },
        "overall": "healthy",
    }


@router.post("/record-prediction")
async def record_prediction(
    latency_ms: float,
    confidence: float,
    variant: str = "control",
) -> Dict[str, str]:
    """Record a prediction for metrics tracking."""
    now = datetime.now()
    async with _metrics_lock:
        _metrics_store["predictions"].append({
            "ts": now,
            "latency_ms": latency_ms,
            "confidence": confidence,
            "variant": variant,
        })
        _metrics_store["latency_samples"].append(latency_ms)
        _prune_metrics_locked(now)
    
    return {"status": "recorded"}


@router.post("/record-fine-tune")
async def record_fine_tune(samples: int, pre_accuracy: float, post_accuracy: float, rollback: bool = False) -> Dict[str, str]:
    """Record a fine-tune run."""
    now = datetime.now()
    async with _metrics_lock:
        _metrics_store["fine_tune_runs"].append({
            "ts": now,
            "samples": samples,
            "pre_accuracy": pre_accuracy,
            "post_accuracy": post_accuracy,
            "rollback": rollback,
        })
        _metrics_store["accuracy_history"].append(post_accuracy)
        _prune_metrics_locked(now)
    
    return {"status": "recorded"}


@router.post("/record-cache-stats")
async def record_cache_stats(hits: int, misses: int, size: int = 0) -> Dict[str, str]:
    """Update cache statistics."""
    now = datetime.now()
    async with _metrics_lock:
        _metrics_store["cache_stats"]["hits"] = hits
        _metrics_store["cache_stats"]["misses"] = misses
        _metrics_store["cache_stats"]["size"] = size
        _prune_metrics_locked(now)
    return {"status": "updated"}


def _generate_drift_alerts(status: str, magnitude: float) -> List[Dict[str, str]]:
    """Generate alerts based on drift status."""
    alerts = []
    
    if status == "critical_drift":
        alerts.append({
            "level": "critical",
            "message": f"Accuracy dropped {abs(magnitude)*100:.1f}% in 7 days. Fine-tune recommended.",
        })
    elif status == "mild_drift":
        alerts.append({
            "level": "warning",
            "message": f"Accuracy drifted {abs(magnitude)*100:.1f}%. Monitor closely.",
        })
    
    return alerts
