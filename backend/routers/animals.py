import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Animal, Herd, Farm, User, UserRole
from backend.schemas import AnimalCreate, HerdCreate, FarmCreate
from backend.security import get_current_user
from backend.services.websocket_manager import ws_manager
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/animals", tags=["Animals & Herds"])

@router.get("")
async def get_animals(
    species: Optional[str] = None,
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Animal)
    # Farmers only see their animals
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(Animal.owner_id == current_user.id)
    elif district:
        stmt = stmt.where(Animal.district == district)
        
    if species:
        stmt = stmt.where(Animal.species == species)
        
    result = await db.execute(stmt)
    animals = result.scalars().all()
    
    # Map to frontend expected shape
    return [
        {
            "id": a.id,
            "tagId": a.tag_id,
            "species": a.species,
            "breed": a.breed or "Indigenous",
            "sex": a.sex,
            "age": a.age_years,
            "ownerName": current_user.full_name if current_user.role == UserRole.FARMER.value else "Farmer",
            "village": a.village,
            "district": a.district,
            "lat": a.lat,
            "lng": a.lng,
            "healthStatus": a.health_status,
            "riskScore": a.risk_score,
            "syncStatus": "Synced"
        }
        for a in animals
    ]

@router.post("")
async def register_animal(
    req: AnimalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    animal_id = f"ANM-{uuid.uuid4().hex[:8].upper()}"
    animal = Animal(
        id=animal_id,
        tag_id=req.tag_id,
        owner_id=current_user.id,
        farm_id=req.farm_id,
        herd_id=req.herd_id,
        species=req.species,
        breed=req.breed,
        sex=req.sex,
        age_years=req.age_years,
        village=req.village or current_user.village or "Shirur",
        district=req.district or current_user.district or "Pune",
        lat=req.lat or 18.5204,
        lng=req.lng or 73.8567,
        health_status="Healthy",
        risk_score=10.0
    )
    db.add(animal)
    await db.commit()
    await db.refresh(animal)
    
    # Real-time WebSocket event
    await ws_manager.broadcast({
        "type": "ANIMAL_REGISTERED",
        "animal": {
            "id": animal.id, "tagId": animal.tag_id, "species": animal.species,
            "district": animal.district, "owner_id": current_user.id
        }
    })
    
    await AuditService.log(
        db, action="ANIMAL_REGISTERED", resource="ANIMAL", resource_id=animal.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role
    )
    
    return {
        "id": animal.id,
        "tagId": animal.tag_id,
        "species": animal.species,
        "breed": animal.breed,
        "sex": animal.sex,
        "age": animal.age_years,
        "ownerName": current_user.full_name,
        "village": animal.village,
        "district": animal.district,
        "healthStatus": animal.health_status,
        "riskScore": animal.risk_score,
        "syncStatus": "Synced"
    }

@router.get("/herds")
async def get_herds(
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Herd)
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(Herd.owner_id == current_user.id)
    elif district:
        stmt = stmt.where(Herd.district == district)
        
    result = await db.execute(stmt)
    herds = result.scalars().all()
    
    return [
        {
            "id": h.id,
            "ownerName": current_user.full_name if current_user.role == UserRole.FARMER.value else "Local Farmer",
            "village": h.village,
            "district": h.district,
            "species": h.species,
            "totalAnimals": h.total_animals,
            "lat": h.lat,
            "lng": h.lng,
            "healthStatus": h.health_status,
            "riskScore": h.risk_score,
            "syncStatus": "Synced"
        }
        for h in herds
    ]

@router.post("/herds")
async def register_herd(
    req: HerdCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    herd_id = f"HRD-{uuid.uuid4().hex[:8].upper()}"
    herd = Herd(
        id=herd_id,
        owner_id=current_user.id,
        farm_id=req.farm_id,
        species=req.species,
        total_animals=req.total_animals,
        village=req.village or current_user.village or "Shirur",
        district=req.district or current_user.district or "Pune",
        lat=req.lat or 18.5204,
        lng=req.lng or 73.8567,
        health_status="Healthy",
        risk_score=15.0
    )
    db.add(herd)
    await db.commit()
    await db.refresh(herd)
    
    return {
        "id": herd.id,
        "ownerName": current_user.full_name,
        "village": herd.village,
        "district": herd.district,
        "species": herd.species,
        "totalAnimals": herd.total_animals,
        "healthStatus": herd.health_status,
        "riskScore": herd.risk_score,
        "syncStatus": "Synced"
    }
