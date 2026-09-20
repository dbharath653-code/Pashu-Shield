from typing import List, Optional
from fastapi import APIRouter
from backend.services.dispatch_service import haversine_distance

router = APIRouter(prefix="/gis", tags=["GIS & Spatial Layers"])

@router.get("/layers")
async def get_gis_layers():
    # Return spatial risk layers for Google Maps / Leaflet
    return {
        "outbreak_clusters": [
            {"id": "CL-01", "name": "Shirur FMD Cluster", "district": "Pune", "lat": 18.8288, "lng": 74.3789, "radius_km": 8.0, "risk_level": "High Risk", "cases": 34},
            {"id": "CL-02", "name": "Khed LSD Hotspot", "district": "Satara", "lat": 17.7122, "lng": 74.0234, "radius_km": 5.0, "risk_level": "High Risk", "cases": 21},
            {"id": "CL-03", "name": "Malegaon PPR Cluster", "district": "Nashik", "lat": 20.5539, "lng": 74.5298, "radius_km": 6.5, "risk_level": "Moderate Risk", "cases": 15}
        ],
        "veterinary_facilities": [
            {"id": "VET-FAC-01", "name": "Shirur Polyclinic & Hospital", "type": "Polyclinic", "district": "Pune", "lat": 18.8260, "lng": 74.3750, "mvu_available": True},
            {"id": "VET-FAC-02", "name": "Satara District Veterinary Hospital", "type": "District Hospital", "district": "Satara", "lat": 17.6850, "lng": 74.0150, "mvu_available": True},
            {"id": "VET-FAC-03", "name": "Nashik Central Polyclinic", "type": "Polyclinic", "district": "Nashik", "lat": 20.0050, "lng": 73.7850, "mvu_available": True}
        ],
        "laboratories": [
            {"id": "LAB-01", "name": "Disease Investigation Section (DIS) Pune", "district": "Pune", "lat": 18.5320, "lng": 73.8450, "status": "Active"},
            {"id": "LAB-02", "name": "Regional Disease Diagnostic Lab (RDDL) Nashik", "district": "Nashik", "lat": 20.0120, "lng": 73.7920, "status": "Active"}
        ]
    }

@router.get("/route")
async def calculate_route(start_lat: float, start_lng: float, dest_lat: float, dest_lng: float):
    dist_km = haversine_distance(start_lat, start_lng, dest_lat, dest_lng)
    est_minutes = int(dist_km * 2.2) # ~25-30 km/h rural road average
    
    # Generate waypoints for navigation visualization
    steps = 5
    waypoints = []
    for i in range(steps + 1):
        ratio = i / steps
        waypoints.append({
            "lat": start_lat + (dest_lat - start_lat) * ratio,
            "lng": start_lng + (dest_lng - start_lng) * ratio
        })
        
    return {
        "distance_km": round(dist_km, 2),
        "estimated_travel_minutes": est_minutes,
        "origin": {"lat": start_lat, "lng": start_lng},
        "destination": {"lat": dest_lat, "lng": dest_lng},
        "waypoints": waypoints
    }
