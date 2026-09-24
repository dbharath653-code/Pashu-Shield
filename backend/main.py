import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.init_db import check_database, seed_database
from backend.middleware import HTTPSRedirectInProduction, RequestContextMiddleware, configure_logging, install_error_handlers
from backend.routers import (alerts, animals, audit, auth, calls, callbacks, cases, external, gis, ivr, labs, ml, reports,
                             surveillance, sync, users, vaccinations, voice)
from backend.services.websocket_manager import ws_manager

configure_logging()
logger = logging.getLogger("pashu_shield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_database()  # create_all only in dev/test; demo seed only when explicitly enabled
    stop = asyncio.Event()
    poller = None
    if settings.JOB_BACKEND == "inline" and settings.ENVIRONMENT != "test":
        from backend.services.jobs import worker_loop
        poller = asyncio.create_task(worker_loop(stop))
        logger.info("inline job poller started (use JOB_BACKEND=worker in production)")
    yield
    stop.set()
    if poller:
        try:
            await asyncio.wait_for(poller, timeout=5)
        except Exception:
            poller.cancel()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION,
              description="Livestock Health Surveillance, Early-Warning, and Veterinary Response Platform for Maharashtra",
              lifespan=lifespan, docs_url=None if settings.is_production else "/docs", redoc_url=None if settings.is_production else "/redoc",
              openapi_url=None if settings.is_production else "/openapi.json")

install_error_handlers(app)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(HTTPSRedirectInProduction)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID", "X-Device-ID"],
                   expose_headers=["X-Request-ID", "X-Total-Count", "X-Next-Offset"])

api_v1 = settings.API_V1_STR
for r in (auth, users, animals, reports, cases, labs, vaccinations, surveillance, gis, alerts, sync, voice, external, audit, ml,
          ivr, calls, callbacks):
    app.include_router(r.router, prefix=api_v1)
app.include_router(external.webhooks, prefix=api_v1)

# Backwards-compatible legacy mounts (same handlers, same auth)
for r in (ml, reports, animals, alerts):
    app.include_router(r.router, prefix="/api")


@app.websocket("/api/v1/ws")
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Authenticated WebSocket. Token is taken from the `Sec-WebSocket-Protocol` header
    ("bearer, <token>") or the `token` query parameter. Client-supplied user_id/role/district
    parameters are ignored; identity comes solely from the verified token."""
    from backend.security import authenticate_token
    origin = websocket.headers.get("origin")
    if origin and settings.CORS_ORIGINS and "*" not in settings.CORS_ORIGINS and origin not in settings.CORS_ORIGINS:
        await websocket.close(code=4403)
        return
    token, subprotocol = websocket.query_params.get("token"), None
    protocols = [p.strip() for p in websocket.headers.get("sec-websocket-protocol", "").split(",") if p.strip()]
    if len(protocols) >= 2 and protocols[0].lower() == "bearer":
        token, subprotocol = protocols[1], "bearer"
    if not token:
        await websocket.close(code=4401)
        return
    async with AsyncSessionLocal() as db:
        try:
            user = await authenticate_token(db, token)
        except Exception:
            await websocket.close(code=4401)
            return
    await websocket.accept(subprotocol=subprotocol)
    conn = await ws_manager.register(websocket, user)
    try:
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                continue
            action = data.get("action")
            from datetime import datetime
            conn.last_seen = datetime.utcnow()
            if action == "PING":
                await websocket.send_json({"type": "PONG", "timestamp": data.get("timestamp")})
            elif action == "SUBSCRIBE" and isinstance(data.get("topics"), list):
                conn.subscriptions = {str(t)[:32] for t in data["topics"][:20]} or {"*"}
    except WebSocketDisconnect:
        ws_manager.disconnect(conn)
    except Exception:
        ws_manager.disconnect(conn)


@app.get("/live")
async def live():
    return {"status": "alive"}


@app.get("/ready")
async def ready():
    checks = {}
    try:
        await check_database()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
    from backend.services.ml_service import ml_service
    checks["ml_model"] = "loaded" if ml_service.model_loaded else "fallback_rules"
    ok = checks["database"] == "ok"
    return JSONResponse(status_code=200 if ok else 503, content={"status": "ready" if ok else "not_ready", "checks": checks})


@app.get("/health")
@app.get("/api/health")
async def health_check():
    try:
        await check_database()
        db_state = "CONNECTED"
    except Exception:
        db_state = "UNAVAILABLE"
    return {"status": "healthy" if db_state == "CONNECTED" else "degraded", "service": settings.PROJECT_NAME, "version": settings.VERSION,
            "state": "Maharashtra", "database": db_state, "environment": settings.ENVIRONMENT, "data_mode": settings.DATA_MODE}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)
