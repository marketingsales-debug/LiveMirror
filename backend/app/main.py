"""
LiveMirror Backend API
FastAPI server for the real-time prediction engine.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.ingest import router as ingest_router
from .api.predict import router as predict_router
from .api.simulate import router as simulate_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("LiveMirror engine starting...")
    yield
    # Shutdown
    print("LiveMirror engine shutting down...")


app = FastAPI(
    title="LiveMirror",
    description="Real-time self-calibrating prediction engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(ingest_router, prefix="/api/ingest", tags=["ingestion"])
app.include_router(predict_router, prefix="/api/predict", tags=["prediction"])
app.include_router(simulate_router, prefix="/api/simulate", tags=["simulation"])
