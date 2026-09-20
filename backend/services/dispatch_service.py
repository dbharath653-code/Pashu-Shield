import math
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import User, UserRole

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth (in km)."""
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
        math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class DispatchEngine:
    @classmethod
    async def find_eligible_veterinarians(
        cls,
        db: AsyncSession,
        district: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        max_distance_km: float = 60.0
    ) -> List[Dict[str, Any]]:
        # Query registered active veterinarians
        stmt = select(User).where(
            User.role.in_([UserRole.VETERINARIAN.value, UserRole.PARA_VET.value]),
            User.is_active == True
        )
        result = await db.execute(stmt)
        all_vets = result.scalars().all()
        
        ranked_vets = []
        for vet in all_vets:
            is_same_district = (vet.district or "").lower() == (district or "").lower()
            
            # Default coordinates for district headquarters if vet lat/lng not set
            vet_lat = 18.5204 if vet.district == "Pune" else 19.7515
            vet_lng = 73.8567 if vet.district == "Pune" else 75.7139
            
            distance_km = 15.0 # fallback default distance
            if lat is not None and lng is not None:
                distance_km = round(haversine_distance(lat, lng, vet_lat, vet_lng), 2)
                
            # Score: same district gets priority bonus, shorter distance gets higher rank
            district_bonus = 50.0 if is_same_district else 0.0
            distance_penalty = min(50.0, distance_km)
            rank_score = district_bonus + (50.0 - distance_penalty)
            
            ranked_vets.append({
                "vet_id": vet.id,
                "full_name": vet.full_name,
                "license_number": vet.license_number,
                "qualification": vet.qualification,
                "specialization": vet.specialization or "General Veterinary Medicine",
                "phone": vet.phone,
                "email": vet.email,
                "district": vet.district,
                "distance_km": distance_km,
                "rank_score": rank_score,
                "is_same_district": is_same_district
            })
            
        # Sort descending by rank score (best matched first)
        ranked_vets.sort(key=lambda x: x["rank_score"], reverse=True)
        return ranked_vets
