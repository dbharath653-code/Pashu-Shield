from fastapi import APIRouter
from backend.services.external_data_service import nadres_provider, census_provider, weather_provider

router = APIRouter(prefix="/external", tags=["External Data Adapters (NADRES / DAHD / Weather)"])

@router.get("/nadres/bulletin")
async def get_nadres_bulletin(state: str = "Maharashtra"):
    return await nadres_provider.fetch_disease_forewarning(state=state)

@router.get("/census/district")
async def get_census_data(district: str = "Pune"):
    return await census_provider.get_district_census(district=district)

@router.get("/weather")
async def get_weather(lat: float = 18.5204, lng: float = 73.8567):
    return await weather_provider.get_district_weather(lat=lat, lng=lng)
