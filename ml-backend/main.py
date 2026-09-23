"""
Standalone ML API (optional separate deployment).

This module no longer contains its own risk engine. It mounts the canonical ML router from
the main backend so there is exactly one implementation (backend/services/ml_service.py).
Run from the repository root:  PYTHONPATH=. uvicorn ml-backend.main:app  (or use backend.main).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402

from backend.routers import ml  # noqa: E402

app = FastAPI(title="Pashu-Shield ML API", description="Thin wrapper around the canonical backend ML service")
app.include_router(ml.router, prefix="/api")
