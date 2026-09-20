import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import VaccinationCampaign, VaccinationRecord, User, UserRole
from backend.schemas import CampaignCreate, VaccinationRecordCreate
from backend.security import get_current_user
from backend.services.websocket_manager import ws_manager
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/vaccination", tags=["Vaccination Management"])

@router.get("/campaigns")
async def get_campaigns(db: AsyncSession = Depends(get_db)):
    stmt = select(VaccinationCampaign).order_by(VaccinationCampaign.start_date.desc())
    campaigns = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": c.id,
            "campaignCode": c.campaign_code,
            "name": c.name,
            "disease": c.disease,
            "vaccine": c.vaccine,
            "species": c.species or ["Cattle", "Buffalo"],
            "targetDistricts": c.target_districts or ["All Maharashtra"],
            "startDate": c.start_date.strftime("%Y-%m-%d"),
            "endDate": c.end_date.strftime("%Y-%m-%d"),
            "status": c.status,
            "targetPopulation": c.target_population,
            "coverageTargetPercent": c.coverage_target_percent,
            "currentVaccinated": c.current_vaccinated
        }
        for c in campaigns
    ]

@router.post("/campaigns")
async def create_campaign(
    req: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaign_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
    campaign = VaccinationCampaign(
        id=campaign_id,
        campaign_code=f"NADCP-MH-{datetime.utcnow().year}-{uuid.uuid4().hex[:4].upper()}",
        name=req.name,
        disease=req.disease,
        vaccine=req.vaccine,
        species=req.species,
        target_districts=req.target_districts,
        start_date=req.start_date,
        end_date=req.end_date,
        status="Active",
        target_population=req.target_population,
        coverage_target_percent=req.coverage_target_percent
    )
    db.add(campaign)
    await db.commit()
    return {"message": "Campaign created", "id": campaign.id}

@router.get("/records")
async def get_vaccinations(
    district: Optional[str] = None,
    disease: Optional[str] = None,
    animal_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(VaccinationRecord).order_by(VaccinationRecord.vaccination_date.desc())
    if animal_id:
        stmt = stmt.where(VaccinationRecord.animal_id == animal_id)
    if district:
        stmt = stmt.where(VaccinationRecord.district == district)
    if disease:
        stmt = stmt.where(VaccinationRecord.disease == disease)
        
    records = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "animalId": r.animal_id,
            "herdId": r.herd_id,
            "species": r.species,
            "disease": r.disease,
            "vaccine": r.vaccine,
            "batchNumber": r.batch_number,
            "vaccinationDate": r.vaccination_date.strftime("%Y-%m-%d"),
            "nextDueDate": r.next_due_date.strftime("%Y-%m-%d") if r.next_due_date else "2026-10-15",
            "campaignId": r.campaign_id,
            "location": r.location or r.district,
            "district": r.district,
            "provider": r.provider_name or "Department of Animal Husbandry",
            "syncStatus": "Synced"
        }
        for r in records
    ]

@router.post("/records")
async def record_vaccination(
    req: VaccinationRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record_id = f"VAC-{uuid.uuid4().hex[:8].upper()}"
    rec = VaccinationRecord(
        id=record_id,
        animal_id=req.animal_id,
        species=req.species,
        disease=req.disease,
        vaccine=req.vaccine,
        batch_number=req.batch_number,
        vaccination_date=req.vaccination_date or datetime.utcnow(),
        next_due_date=req.next_due_date,
        campaign_id=req.campaign_id,
        provider_id=current_user.id,
        provider_name=current_user.full_name,
        district=req.district,
        location=req.location or req.district
    )
    db.add(rec)
    await db.commit()
    
    await AuditService.log(
        db, action="VACCINATION_RECORDED", resource="VACCINATION", resource_id=rec.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role
    )
    return {"message": "Vaccination recorded", "id": rec.id}
