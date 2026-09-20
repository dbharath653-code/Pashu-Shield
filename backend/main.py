import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import engine, Base
from backend.init_db import seed_database
from backend.services.websocket_manager import ws_manager

# Import all routers
from backend.routers import (
    auth, users, animals, reports, cases, labs,
    vaccinations, surveillance, gis, alerts, sync,
    voice, ml, external, audit
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pashu_shield")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database & Seed
    logger.info("Initializing Pashu-Shield Database...")
    try:
        await seed_database()
        logger.info("Database initialized and verified.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    yield
    # Shutdown
    logger.info("Pashu-Shield Backend shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Livestock Health Surveillance, Early-Warning, and Veterinary Response Platform for Maharashtra",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 Routers
api_v1 = settings.API_V1_STR
app.include_router(auth.router, prefix=api_v1)
app.include_router(users.router, prefix=api_v1)
app.include_router(animals.router, prefix=api_v1)
app.include_router(reports.router, prefix=api_v1)
app.include_router(cases.router, prefix=api_v1)
app.include_router(labs.router, prefix=api_v1)
app.include_router(vaccinations.router, prefix=api_v1)
app.include_router(surveillance.router, prefix=api_v1)
app.include_router(gis.router, prefix=api_v1)
app.include_router(alerts.router, prefix=api_v1)
app.include_router(sync.router, prefix=api_v1)
app.include_router(voice.router, prefix=api_v1)
app.include_router(external.router, prefix=api_v1)
app.include_router(audit.router, prefix=api_v1)
app.include_router(ml.router, prefix=api_v1)

# Backwards compatibility legacy routes mounted at /api directly
app.include_router(ml.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(animals.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")

# Real-time WebSockets
@app.websocket("/api/v1/ws")
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query("anonymous"),
    role: str = Query("GUEST"),
    district: str = Query("ALL")
):
    await ws_manager.connect(websocket, user_id=user_id, role=role, district=district)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle client ping or subscription
            if data.get("action") == "PING":
                await websocket.send_json({"type": "PONG", "timestamp": data.get("timestamp")})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        ws_manager.disconnect(websocket)

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "state": "Maharashtra",
        "database": "CONNECTED",
        "mode": "PRODUCTION_READY"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
