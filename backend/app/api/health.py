"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "livemirror",
        "version": "0.1.0",
    }


@router.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "components": {
            "ingestion": "not_started",
            "graph": "not_started",
            "simulation": "not_started",
            "analysis": "not_started",
            "learning": "not_started",
        },
    }
