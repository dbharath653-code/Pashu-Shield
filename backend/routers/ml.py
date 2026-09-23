"""ML endpoints (canonical engine: backend/services/ml_service.py; ml-backend/ re-mounts this).

Contract changes (additive): responses now include `status` (OK | INSUFFICIENT_DATA | FALLBACK),
`model` metadata and a `label` stating predictions are not diagnoses. Request defaults that
previously fabricated inputs (population 15000, cases 45 ...) were removed — missing features
now yield INSUFFICIENT_DATA instead of a confident-looking score.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import User
from backend.security import Permission, get_current_user_optional, require_permission
from backend.services.ml_service import ml_service
from backend.services.outbreak_service import detect_clusters

router = APIRouter(tags=["Machine Learning & AI Early Warning"])


class PredictReq(BaseModel):
    disease: str = Field(default="LSD", max_length=64)
    district: Optional[str] = Field(default=None, max_length=128)
    time_range: Optional[str] = Field(default=None, max_length=8)
    animal_population: Optional[float] = Field(default=None, ge=0)
    affected_animals: Optional[float] = Field(default=None, ge=0)
    new_cases: Optional[float] = Field(default=None, ge=0)
    deaths: Optional[float] = Field(default=None, ge=0)
    vaccination_coverage: Optional[float] = Field(default=None, ge=0, le=1)
    temperature: Optional[float] = Field(default=None, ge=-20, le=60)
    rainfall: Optional[float] = Field(default=None, ge=0)
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    animal_density: Optional[float] = Field(default=None, ge=0)
    previous_cases: Optional[float] = Field(default=None, ge=0)
    cases_growth_rate: Optional[float] = Field(default=None, ge=-1, le=100)


class OutbreakReq(BaseModel):
    new_cases: float = Field(ge=0)
    cases_growth_rate: float = Field(ge=-1, le=100)
    deaths: float = Field(ge=0)
    district: Optional[str] = Field(default=None, max_length=128)


class ForecastReq(BaseModel):
    historical_cases: List[float] = Field(default_factory=list, max_length=730)
    horizon: int = Field(default=14, ge=1, le=60)


class ClusterReq(BaseModel):
    districts: Optional[List[str]] = None
    disease: Optional[str] = None
    days: int = Field(default=21, ge=1, le=180)


@router.post("/predict")
@router.post("/v1/ml/predict")
async def predict_risk(req: PredictReq, current_user: User = Depends(require_permission(Permission.ML_RUN))):
    return ml_service.predict_risk(req.model_dump())


@router.get("/model-performance")
@router.get("/v1/ml/performance")
async def get_performance(current_user: Optional[User] = Depends(get_current_user_optional)):
    return ml_service.metrics


@router.get("/v1/ml/model-card")
async def model_card():
    return ml_service.model_info()


@router.post("/outbreak-detection")
@router.post("/v1/ml/outbreak")
async def detect_outbreak(req: OutbreakReq, current_user: User = Depends(require_permission(Permission.ML_RUN))):
    return ml_service.detect_outbreak(req.model_dump())


@router.post("/forecast")
@router.post("/v1/ml/forecast")
async def get_forecast(req: ForecastReq, current_user: User = Depends(require_permission(Permission.ML_RUN))):
    return ml_service.forecast(req.historical_cases, req.horizon)


@router.post("/cluster")
@router.post("/v1/ml/cluster")
async def spatiotemporal_clustering(req: ClusterReq, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.ML_RUN))):
    """Real density clustering over stored reports/observations (replaces random clusters)."""
    result = await detect_clusters(db, days=req.days, disease=req.disease)
    if req.districts:
        wanted = {d.lower() for d in req.districts}
        result["clusters"] = [c for c in result["clusters"] if (c.get("district") or "").lower() in wanted]
    result["status"] = "OK" if result["clusters"] else ("INSUFFICIENT_DATA" if result["records_with_coordinates"] < 2 else "NO_CLUSTERS")
    return result
