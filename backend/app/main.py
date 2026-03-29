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
from .api.stream import router as stream_router
from .api.metrics import router as metrics_router
from backend.self_mirror.main import router as self_mirror_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup — wire shared graph between ingestion and simulation
    print("LiveMirror engine starting...")
    try:
        from .api.ingest import get_pipeline
        from .api.simulate import set_graph
        pipeline = get_pipeline()
        set_graph(pipeline.graph)
        print("LiveMirror: Pipeline → Simulation graph wired.")
    except Exception as e:
        print(f"LiveMirror: Graph wiring skipped ({e})")

    # Try connecting Redis event bus
    try:
        from .api.stream import event_bus
        if hasattr(event_bus, 'connect'):
            await event_bus.connect()
    except Exception as e:
        print(f"LiveMirror: Redis connection skipped ({e})")

    yield

    # Shutdown — close Redis
    try:
        from .api.stream import event_bus
        if hasattr(event_bus, 'close'):
            await event_bus.close()
    except Exception:
        pass
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

# Root health check for Docker/load balancer
@app.get("/health")
async def root_health():
    """Root health check for Docker/Kubernetes."""
    return {"status": "ok"}


# Routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(ingest_router, prefix="/api/ingest", tags=["ingestion"])
app.include_router(predict_router, prefix="/api/predict", tags=["prediction"])
app.include_router(simulate_router, prefix="/api/simulate", tags=["simulation"])
app.include_router(stream_router, prefix="/api/stream", tags=["real-time"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["monitoring"])
app.include_router(self_mirror_router, prefix="/api/self-mirror", tags=["autonomous"])
