"""Ingestion API endpoints — trigger data collection from platforms."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class IngestRequest(BaseModel):
    """Request to ingest data for a topic."""
    topic: str
    platforms: Optional[List[str]] = None  # None = all platforms
    timeframe_hours: int = 720  # default 30 days
    max_results_per_platform: int = 100


class IngestResponse(BaseModel):
    """Response from ingestion."""
    job_id: str
    topic: str
    platforms: List[str]
    status: str


@router.post("/start", response_model=IngestResponse)
async def start_ingestion(request: IngestRequest):
    """Start data ingestion for a topic across platforms."""
    # TODO: implement actual ingestion pipeline
    return IngestResponse(
        job_id="ingest_placeholder",
        topic=request.topic,
        platforms=request.platforms or ["reddit", "twitter", "youtube"],
        status="queued",
    )


@router.get("/status/{job_id}")
async def ingestion_status(job_id: str):
    """Check ingestion job status."""
    return {"job_id": job_id, "status": "not_implemented"}
