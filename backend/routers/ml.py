from typing import Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.ml_service import ml_service

router = APIRouter(tags=["Machine Learning & AI Early Warning"])

class PredictReq(BaseModel):
    disease: str = "LSD"
    district: str = "Pune"
    time_range: str = "14"
    animal_population: float = 15000.0
    affected_animals: float = 120.0
    new_cases: float = 45.0
    deaths: float = 5.0
    vaccination_coverage: float = 0.45
    temperature: float = 32.5
    rainfall: float = 12.0
    humidity: float = 65.0
    animal_density: float = 120.5
    previous_cases: float = 300.0
    cases_growth_rate: float = 0.15

class OutbreakReq(BaseModel):
    new_cases: float
    cases_growth_rate: float
    deaths: float
    district: str = "Pune"

class ForecastReq(BaseModel):
    historical_cases: List[float] = [20.0, 35.0, 48.0, 60.0]
    horizon: int = 14

class ClusterReq(BaseModel):
    districts: List[str] = ["Pune", "Satara", "Nashik"]

@router.post("/predict")
@router.post("/v1/ml/predict")
async def predict_risk(req: PredictReq):
    return ml_service.predict_risk(req.model_dump())

@router.get("/model-performance")
@router.get("/v1/ml/performance")
async def get_performance():
    return ml_service.metrics

@router.post("/outbreak-detection")
@router.post("/v1/ml/outbreak")
async def detect_outbreak(req: OutbreakReq):
    return ml_service.detect_outbreak(req.model_dump())

@router.post("/forecast")
@router.post("/v1/ml/forecast")
async def get_forecast(req: ForecastReq):
    return ml_service.forecast(req.historical_cases, req.horizon)

@router.post("/cluster")
@router.post("/v1/ml/cluster")
async def spatiotemporal_clustering(req: ClusterReq):
    return ml_service.spatiotemporal_clustering(req.districts)
