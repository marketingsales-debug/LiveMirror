"""
LiveMirror Backend API
FastAPI server for the real-time prediction engine.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

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
    print("LiveMirror engine starting...")
    try:
        from .api.ingest import get_pipeline
        from .api.simulate import set_graph
        pipeline = get_pipeline()
        set_graph(pipeline.graph)
        print("LiveMirror: Pipeline → Simulation graph wired.")
    except Exception as e:
        print(f"LiveMirror: Graph wiring skipped ({e})")

    try:
        from .api.stream import event_bus
        if hasattr(event_bus, 'connect'):
            await event_bus.connect()
    except Exception as e:
        print(f"LiveMirror: Redis connection skipped ({e})")

    yield

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

# CORS — allow everything for cloud tunneling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root health check
@app.get("/health")
async def root_health():
    return {"status": "ok"}

# API Routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(ingest_router, prefix="/api/ingest", tags=["ingestion"])
app.include_router(predict_router, prefix="/api/predict", tags=["prediction"])
app.include_router(simulate_router, prefix="/api/simulate", tags=["simulation"])
app.include_router(stream_router, prefix="/api/stream", tags=["real-time"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["monitoring"])
app.include_router(self_mirror_router, prefix="/api/self-mirror", tags=["autonomous"])

# --- Robust Frontend Serving (SPA Pattern) ---

# 1. Resolve Frontend Path
# We check multiple levels to handle Kaggle's potential nested cloning
current_dir = os.path.dirname(__file__)
possible_paths = [
    os.path.abspath(os.path.join(current_dir, "..", "..", "frontend", "dist")),
    os.path.abspath(os.path.join(current_dir, "..", "frontend", "dist")),
    "/kaggle/working/LiveMirror/frontend/dist",
    "/kaggle/working/LiveMirror/LiveMirror/frontend/dist"
]

frontend_path = None
for p in possible_paths:
    if os.path.exists(os.path.join(p, "index.html")):
        frontend_path = p
        print(f"✅ Found frontend assets at: {frontend_path}")
        break

if frontend_path:
    # Mount static assets (css, js, images)
    # Note: We mount to /assets or similar if possible, but for SPA we often mount to /
    # To avoid colliding with /api, we mount this LAST
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="static")

    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        # If it looks like an API call but reached here, it's a 404
        if catchall.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "API Route Not Found"})
        
        # Otherwise, serve index.html (SPA routing)
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    @app.get("/")
    async def root_fallback():
        return {
            "status": "online",
            "message": "LiveMirror Backend Active. Frontend build not found.",
            "search_locations": possible_paths,
            "api_docs": "/docs"
        }
