"""
Ingestion API endpoints — trigger data collection from platforms.
Owner: Claude

Wires the frontend to the real LiveMirrorPipeline for live data ingestion.
"""

import asyncio
import uuid
import sys
import os
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, conint, constr
from typing import List, Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.pipeline.orchestrator import LiveMirrorPipeline
from src.ingestion.platforms.reddit import RedditIngester
from src.ingestion.platforms.hackernews import HackerNewsIngester
from src.ingestion.platforms.polymarket import PolymarketIngester
from src.ingestion.platforms.web_search import WebSearchIngester
from src.ingestion.platforms.twitter import TwitterIngester
from src.ingestion.platforms.youtube import YouTubeIngester
from src.ingestion.platforms.bluesky import BlueskyIngester
from src.ingestion.platforms.news import NewsIngester
from src.ingestion.platforms.tiktok import TikTokIngester
from src.ingestion.platforms.instagram import InstagramIngester
from src.shared.types import Platform
from .metrics import record_cache_stats

router = APIRouter()
logger = logging.getLogger(__name__)

# Track running jobs
_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = asyncio.Lock()
_JOB_TTL = timedelta(hours=12)
_MAX_JOBS = 1000

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
        _pipeline.register_ingester(TwitterIngester())
        _pipeline.register_ingester(YouTubeIngester())
        _pipeline.register_ingester(BlueskyIngester())
        _pipeline.register_ingester(NewsIngester())
        _pipeline.register_ingester(TikTokIngester())
        _pipeline.register_ingester(InstagramIngester())
    return _pipeline


def get_pipeline() -> LiveMirrorPipeline:
    """Public accessor for sharing pipeline graph with simulation API."""
    return _get_pipeline()


def _prune_jobs_locked(now: datetime) -> None:
    cutoff = now - _JOB_TTL
    expired = [
        job_id
        for job_id, job in _jobs.items()
        if job.get("created_at") and job["created_at"] < cutoff
    ]
    for job_id in expired:
        _jobs.pop(job_id, None)
    if len(_jobs) > _MAX_JOBS:
        overflow = len(_jobs) - _MAX_JOBS
        for job_id, _ in sorted(
            _jobs.items(),
            key=lambda item: item[1].get("created_at", now),
        )[:overflow]:
            _jobs.pop(job_id, None)


class IngestRequest(BaseModel):
    """Request to ingest data for a topic."""
    topic: constr(strip_whitespace=True, min_length=1, max_length=200)
    platforms: Optional[List[Platform]] = Field(default=None, min_items=1)
    max_results_per_platform: conint(ge=1, le=500) = 50


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
    now = datetime.now()

    # Resolve platform filter
    platform_names = (
        [platform.value for platform in request.platforms]
        if request.platforms
        else [p.value for p in pipeline.ingestion.available_platforms]
    )

    async with _jobs_lock:
        _prune_jobs_locked(now)
        _jobs[job_id] = {
            "topic": request.topic,
            "status": "running",
            "platforms": platform_names,
            "result": None,
            "error": None,
            "created_at": now,
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
        
        # Record cache stats for monitoring
        cache_stats = pipeline.fusion.cache.stats()
        await record_cache_stats(
            hits=cache_stats["hits"], 
            misses=cache_stats["misses"], 
            size=cache_stats["size"]
        )

        now = datetime.now()
        async with _jobs_lock:
            _prune_jobs_locked(now)
            job = _jobs.get(job_id)
            if not job:
                return
            job["status"] = "completed"
            job["result"] = {
                "query": result["query"],
                "signals_found": len(result["scored_signals"]),
                "analysis_count": len(result["analysis_results"]),
                "graph_stats": result["graph_stats"],
                "timing": result["timing"],
            }
    except Exception as e:
        now = datetime.now()
        async with _jobs_lock:
            _prune_jobs_locked(now)
            job = _jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["error"] = str(e)
        logger.exception("[IngestAPI] Job %s failed", job_id)


@router.get("/status/{job_id}")
async def ingestion_status(job_id: str):
    """Check ingestion job status."""
    now = datetime.now()
    async with _jobs_lock:
        _prune_jobs_locked(now)
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
