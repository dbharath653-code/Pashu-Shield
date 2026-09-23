import uuid
from datetime import datetime
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import Animal, User, UserRole, VaccinationCampaign, VaccinationRecord
from backend.schemas import CampaignCreate, VaccinationRecordCreate
from backend.security import Permission, ensure_can_access_record, require_permission, resolve_district_filter
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/vaccination", tags=["Vaccination Management"])


@router.get("/campaigns")
async def get_campaigns(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VACCINATION_READ))):
    stmt = select(VaccinationCampaign).order_by(VaccinationCampaign.start_date.desc())
    if settings.DATA_MODE == "live":
        stmt = stmt.where(VaccinationCampaign.is_demo.is_(False))
    campaigns = (await db.execute(stmt)).scalars().all()
    return [{"id": c.id, "campaignCode": c.campaign_code, "name": c.name, "disease": c.disease, "vaccine": c.vaccine, "species": c.species or [],
             "targetDistricts": c.target_districts or [], "startDate": c.start_date.strftime("%Y-%m-%d"), "endDate": c.end_date.strftime("%Y-%m-%d"),
             "status": c.status, "targetPopulation": c.target_population, "coverageTargetPercent": c.coverage_target_percent,
             "currentVaccinated": c.current_vaccinated, "isDemo": c.is_demo} for c in campaigns]


@router.post("/campaigns")
async def create_campaign(req: CampaignCreate, request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_permission(Permission.VACCINATION_MANAGE))):
    campaign = VaccinationCampaign(id=f"CMP-{uuid.uuid4().hex[:8].upper()}", campaign_code=f"NADCP-MH-{datetime.utcnow().year}-{uuid.uuid4().hex[:4].upper()}",
                                   status="Active", created_by=current_user.id, is_demo=current_user.is_demo, **req.model_dump())
    db.add(campaign)
    await AuditService.for_user(db, current_user, "CAMPAIGN_CREATED", "VACCINATION_CAMPAIGN", campaign.id, request=request, commit=False)
    await db.commit()
    return {"message": "Campaign created", "id": campaign.id}


@router.get("/records")
async def get_vaccinations(district: Optional[str] = None, disease: Optional[str] = None, animal_id: Optional[str] = None,
                           limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
                           db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VACCINATION_READ))):
    stmt = select(VaccinationRecord).where(VaccinationRecord.deleted_at.is_(None))
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(VaccinationRecord.animal_id.in_(select(Animal.id).where(Animal.owner_id == current_user.id)))
    else:
        d = resolve_district_filter(current_user, district)
        if d:
            stmt = stmt.where(VaccinationRecord.district == d)
    if animal_id:
        stmt = stmt.where(VaccinationRecord.animal_id == animal_id)
    if disease:
        stmt = stmt.where(VaccinationRecord.disease == disease)
    records = (await db.execute(stmt.order_by(VaccinationRecord.vaccination_date.desc()).offset(offset).limit(limit))).scalars().all()
    return [{"id": r.id, "animalId": r.animal_id, "herdId": r.herd_id, "species": r.species, "disease": r.disease, "vaccine": r.vaccine,
             "batchNumber": r.batch_number, "doseNumber": r.dose_number, "vaccinationDate": r.vaccination_date.strftime("%Y-%m-%d"),
             "nextDueDate": r.next_due_date.strftime("%Y-%m-%d") if r.next_due_date else None, "campaignId": r.campaign_id,
             "location": r.location or r.district, "district": r.district, "provider": r.provider_name, "status": r.status,
             "adverseEvent": r.adverse_event, "version": r.version, "syncStatus": "Synced"} for r in records]


async def create_vaccination_record(db: AsyncSession, req: VaccinationRecordCreate, user: User, device_id: Optional[str] = None) -> Tuple[VaccinationRecord, bool]:
    """Returns (record, was_duplicate). Duplicate = same animal + disease + dose on the same day."""
    when = (req.vaccination_date.replace(tzinfo=None) if req.vaccination_date else datetime.utcnow())
    day = when.strftime("%Y-%m-%d")
    dup = (await db.execute(select(VaccinationRecord).where(VaccinationRecord.animal_id == req.animal_id, VaccinationRecord.disease == req.disease,
                                                            VaccinationRecord.dose_number == req.dose_number, VaccinationRecord.vaccination_day == day))).scalars().first()
    if dup:
        return dup, True
    animal = await db.get(Animal, req.animal_id)
    if animal:
        ensure_can_access_record(user, owner_ids=[animal.owner_id], district=animal.district)
    rec = VaccinationRecord(id=req.id or f"VAC-{uuid.uuid4().hex[:8].upper()}", vaccination_date=when, vaccination_day=day, provider_id=user.id,
                            provider_name=user.full_name, location=req.location or req.district, updated_by=user.id, device_id=device_id, is_demo=user.is_demo,
                            status="Adverse event reported" if req.adverse_event else "Administered",
                            **req.model_dump(exclude={"id", "vaccination_date", "location"}))
    db.add(rec)
    if req.campaign_id:
        camp = await db.get(VaccinationCampaign, req.campaign_id)
        if camp:
            camp.current_vaccinated = (camp.current_vaccinated or 0) + 1
    await db.flush()
    return rec, False


@router.post("/records")
async def record_vaccination(req: VaccinationRecordCreate, request: Request, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(require_permission(Permission.VACCINATION_RECORD))):
    try:
        rec, duplicate = await create_vaccination_record(db, req, current_user)
    except IntegrityError:
        await db.rollback()
        return {"message": "Duplicate vaccination (same animal, disease, dose and day) — not recorded twice", "duplicate": True}
    if duplicate:
        return {"message": "Duplicate vaccination (same animal, disease, dose and day) — not recorded twice", "id": rec.id, "duplicate": True}
    await AuditService.for_user(db, current_user, "VACCINATION_RECORDED", "VACCINATION", rec.id, request=request, commit=False)
    await db.commit()
    return {"message": "Vaccination recorded", "id": rec.id, "duplicate": False}
