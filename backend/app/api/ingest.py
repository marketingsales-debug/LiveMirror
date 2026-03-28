"""
Ingestion API endpoints — trigger data collection from platforms.
Owner: Claude

Wires the frontend to the real LiveMirrorPipeline for live data ingestion.
"""

import asyncio
import uuid
import sys
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.pipeline.orchestrator import LiveMirrorPipeline
from src.ingestion.platforms.reddit import RedditIngester
from src.ingestion.platforms.hackernews import HackerNewsIngester
from src.ingestion.platforms.polymarket import PolymarketIngester
from src.ingestion.platforms.web_search import WebSearchIngester
from src.shared.types import Platform

router = APIRouter()

# Track running jobs
_jobs: Dict[str, Dict[str, Any]] = {}

# Shared pipeline instance — initialized lazily
_pipeline: Optional[LiveMirrorPipeline] = None


def _get_pipeline() -> LiveMirrorPipeline:
    """Get or create the shared pipeline with all ingesters registered."""
    global _pipeline
    if _pipeline is None:
        _pipeline = LiveMirrorPipeline()
        _pipeline.register_ingester(RedditIngester())
        _pipeline.register_ingester(HackerNewsIngester())
        _pipeline.register_ingester(PolymarketIngester())
        _pipeline.register_ingester(WebSearchIngester())
    return _pipeline


def get_pipeline() -> LiveMirrorPipeline:
    """Public accessor for sharing pipeline graph with simulation API."""
    return _get_pipeline()


class IngestRequest(BaseModel):
    """Request to ingest data for a topic."""
    topic: str
    platforms: Optional[List[str]] = None
    max_results_per_platform: int = 50


class IngestResponse(BaseModel):
    """Response from ingestion."""
    job_id: str
    topic: str
    platforms: List[str]
    status: str


@router.post("/start", response_model=IngestResponse)
async def start_ingestion(request: IngestRequest, background_tasks: BackgroundTasks):
    """Start data ingestion for a topic across platforms."""
    pipeline = _get_pipeline()
    job_id = f"ingest_{uuid.uuid4().hex[:12]}"

    # Resolve platform filter
    platform_names = request.platforms or [p.value for p in pipeline.ingestion.available_platforms]

    _jobs[job_id] = {
        "topic": request.topic,
        "status": "running",
        "platforms": platform_names,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(
        _run_ingestion_bg, job_id, request.topic, request.max_results_per_platform
    )

    return IngestResponse(
        job_id=job_id,
        topic=request.topic,
        platforms=platform_names,
        status="running",
    )


async def _run_ingestion_bg(job_id: str, topic: str, max_results: int) -> None:
    """Background task that runs the full pipeline."""
    pipeline = _get_pipeline()
    try:
        result = await pipeline.run(topic, max_results_per_platform=max_results)
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["result"] = {
            "query": result["query"],
            "signals_found": len(result["scored_signals"]),
            "analysis_count": len(result["analysis_results"]),
            "graph_stats": result["graph_stats"],
            "timing": result["timing"],
        }
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        print(f"[IngestAPI] Job {job_id} failed: {e}")


@router.get("/status/{job_id}")
async def ingestion_status(job_id: str):
    """Check ingestion job status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "topic": job["topic"],
        "status": job["status"],
        "platforms": job["platforms"],
        "result": job["result"],
        "error": job["error"],
    }


@router.get("/health")
async def platform_health():
    """Check health of all registered ingesters."""
    pipeline = _get_pipeline()
    health = await pipeline.ingestion.health_check_all()
    return {"platforms": health}
