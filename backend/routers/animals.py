import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Animal, Herd, User, UserRole
from backend.schemas import AnimalCreate, HerdCreate
from backend.security import Permission, require_permission, resolve_district_filter
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/animals", tags=["Animals & Herds"])


def _loc(obj):
    return {"lat": obj.lat, "lng": obj.lng, "locationStatus": "LOCATION_UNAVAILABLE" if obj.lat is None else "USER_ENTERED"}


def _animal(a: Animal, owner_name: Optional[str]) -> dict:
    return {"id": a.id, "tagId": a.tag_id, "species": a.species, "breed": a.breed, "sex": a.sex, "age": a.age_years, "ownerName": owner_name,
            "village": a.village, "district": a.district, **_loc(a), "healthStatus": a.health_status, "riskScore": a.risk_score,
            "version": a.version, "syncStatus": "Synced"}


def _herd(h: Herd, owner_name: Optional[str]) -> dict:
    return {"id": h.id, "ownerName": owner_name, "village": h.village, "district": h.district, "species": h.species, "totalAnimals": h.total_animals,
            **_loc(h), "healthStatus": h.health_status, "riskScore": h.risk_score, "version": h.version, "syncStatus": "Synced"}


async def _owner_names(db, ids):
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict((await db.execute(select(User.id, User.full_name).where(User.id.in_(ids)))).all())


@router.get("")
async def get_animals(species: Optional[str] = None, district: Optional[str] = None, limit: int = Query(500, ge=1, le=2000), offset: int = Query(0, ge=0),
                      db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.ANIMAL_READ))):
    stmt = select(Animal).where(Animal.deleted_at.is_(None))
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(Animal.owner_id == current_user.id)
    else:
        d = resolve_district_filter(current_user, district)
        if d:
            stmt = stmt.where(Animal.district == d)
    if species:
        stmt = stmt.where(Animal.species == species)
    animals = (await db.execute(stmt.order_by(Animal.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    names = await _owner_names(db, [a.owner_id for a in animals])
    return [_animal(a, names.get(a.owner_id)) for a in animals]


@router.post("")
async def register_animal(req: AnimalCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.ANIMAL_WRITE))):
    # No invented coordinates: missing location stays null (LOCATION_UNAVAILABLE).
    animal = Animal(id=req.id or f"ANM-{uuid.uuid4().hex[:8].upper()}", owner_id=current_user.id, updated_by=current_user.id, is_demo=current_user.is_demo,
                    health_status="Healthy", risk_score=0.0, **req.model_dump(exclude={"id"}))
    db.add(animal)
    await AuditService.for_user(db, current_user, "ANIMAL_REGISTERED", "ANIMAL", animal.id, request=request, commit=False)
    await db.commit()
    return _animal(animal, current_user.full_name)


@router.get("/herds")
async def get_herds(district: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.ANIMAL_READ))):
    stmt = select(Herd).where(Herd.deleted_at.is_(None))
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(Herd.owner_id == current_user.id)
    else:
        d = resolve_district_filter(current_user, district)
        if d:
            stmt = stmt.where(Herd.district == d)
    herds = (await db.execute(stmt.limit(1000))).scalars().all()
    names = await _owner_names(db, [h.owner_id for h in herds])
    return [_herd(h, names.get(h.owner_id)) for h in herds]


@router.post("/herds")
async def register_herd(req: HerdCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.ANIMAL_WRITE))):
    herd = Herd(id=req.id or f"HRD-{uuid.uuid4().hex[:8].upper()}", owner_id=current_user.id, updated_by=current_user.id, is_demo=current_user.is_demo,
                health_status="Healthy", risk_score=0.0, **req.model_dump(exclude={"id"}))
    db.add(herd)
    await AuditService.for_user(db, current_user, "HERD_REGISTERED", "HERD", herd.id, request=request, commit=False)
    await db.commit()
    return _herd(herd, current_user.full_name)
