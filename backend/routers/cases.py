import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import VeterinaryCase, VeterinaryVisit, User, UserRole, LabSample
from backend.schemas import CaseStatusUpdate, CaseAssignRequest, VisitCreate
from backend.security import get_current_user, require_roles
from backend.services.websocket_manager import ws_manager
from backend.services.notification_service import NotificationService
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/cases", tags=["Veterinary Cases & Dispatch"])

@router.get("")
async def get_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(VeterinaryCase).order_by(VeterinaryCase.created_at.desc())
    
    # Role-based visibility
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(VeterinaryCase.farmer_id == current_user.id)
    elif current_user.role in [UserRole.VETERINARIAN.value, UserRole.PARA_VET.value]:
        # Vets see their assigned cases OR unassigned cases in their district
        stmt = stmt.where(
            (VeterinaryCase.assigned_vet_id == current_user.id) |
            ((VeterinaryCase.district == current_user.district) & (VeterinaryCase.assigned_vet_id == None))
        )
    elif district:
        stmt = stmt.where(VeterinaryCase.district == district)
        
    if status:
        stmt = stmt.where(VeterinaryCase.status == status)
    if priority:
        stmt = stmt.where(VeterinaryCase.priority == priority)
        
    result = await db.execute(stmt)
    cases = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "caseNumber": c.case_number,
            "animalHerdId": c.animal_id or f"ANM-{c.id[-6:]}",
            "species": c.species,
            "location": f"{c.village}, {c.district}",
            "district": c.district,
            "village": c.village,
            "lat": c.lat or 18.5204,
            "lng": c.lng or 73.8567,
            "reportedProblem": c.reported_problem or "Syndromic signs observed",
            "riskScore": c.risk_score,
            "priority": c.priority,
            "reportedAt": c.created_at.strftime("%d %b %Y, %I:%M %p"),
            "assignedVet": c.assigned_vet_id,
            "status": c.status,
            "diagnosis": c.diagnosis,
            "treatmentPrescribed": c.treatment_prescribed,
            "syncStatus": "Synced"
        }
        for c in cases
    ]

@router.get("/{case_id}")
async def get_case_detail(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(VeterinaryCase).where(VeterinaryCase.id == case_id)
    c = (await db.execute(stmt)).scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Get visits
    visit_stmt = select(VeterinaryVisit).where(VeterinaryVisit.case_id == case_id)
    visits = (await db.execute(visit_stmt)).scalars().all()
    
    # Get associated lab samples
    sample_stmt = select(LabSample).where(LabSample.case_id == case_id)
    samples = (await db.execute(sample_stmt)).scalars().all()

    return {
        "id": c.id,
        "caseNumber": c.case_number,
        "species": c.species,
        "location": f"{c.village}, {c.district}",
        "district": c.district,
        "village": c.village,
        "lat": c.lat,
        "lng": c.lng,
        "reportedProblem": c.reported_problem,
        "riskScore": c.risk_score,
        "priority": c.priority,
        "reportedAt": c.created_at.isoformat(),
        "assignedVet": c.assigned_vet_id,
        "status": c.status,
        "diagnosis": c.diagnosis,
        "treatmentPrescribed": c.treatment_prescribed,
        "visits": [
            {
                "id": v.id,
                "visitDate": v.visit_date.isoformat(),
                "observations": v.observations,
                "treatmentGiven": v.treatment_given,
                "followUpNeeded": v.follow_up_needed,
                "followUpDate": v.follow_up_date.isoformat() if v.follow_up_date else None
            }
            for v in visits
        ],
        "samples": [
            {
                "id": s.id,
                "sampleCode": s.sample_code,
                "status": s.status,
                "diseaseSuspected": s.disease_suspected,
                "sampleType": s.sample_type
            }
            for s in samples
        ]
    }

@router.patch("/{case_id}/status")
async def update_case_status(
    case_id: str,
    req: CaseStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(VeterinaryCase).where(VeterinaryCase.id == case_id)
    case = (await db.execute(stmt)).scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    old_status = case.status
    case.status = req.status
    now = datetime.utcnow()
    
    if req.status == "ACCEPTED":
        case.accepted_at = now
        if not case.assigned_vet_id:
            case.assigned_vet_id = current_user.id
    elif req.status == "EN_ROUTE" or req.status == "En Route":
        case.en_route_at = now
    elif req.status == "ON_SITE":
        case.on_site_at = now
    elif req.status in ["RESOLVED", "Resolved", "CLOSED", "Closed"]:
        case.resolved_at = now
        case.closed_at = now
        
    if req.diagnosis:
        case.diagnosis = req.diagnosis
    if req.treatment_prescribed:
        case.treatment_prescribed = req.treatment_prescribed
        
    await db.commit()
    await db.refresh(case)
    
    # Real-time WebSocket broadcast
    await ws_manager.broadcast({
        "type": "CASE_STATUS_CHANGED",
        "case": {
            "id": case.id,
            "caseNumber": case.case_number,
            "status": case.status,
            "updated_by": current_user.full_name,
            "role": current_user.role
        }
    })
    
    # Audit log
    await AuditService.log(
        db, action="CASE_STATUS_UPDATED", resource="CASE", resource_id=case.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role,
        old_value={"status": old_status}, new_value={"status": case.status}
    )
    
    return {"message": "Case updated successfully", "case": case}

@router.post("/{case_id}/visits")
async def record_visit(
    case_id: str,
    req: VisitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visit = VeterinaryVisit(
        id=f"VST-{uuid.uuid4().hex[:8].upper()}",
        case_id=case_id,
        vet_id=current_user.id,
        visit_date=datetime.utcnow(),
        observations=req.observations,
        treatment_given=req.treatment_given,
        follow_up_needed=req.follow_up_needed,
        follow_up_date=req.follow_up_date
    )
    db.add(visit)
    await db.commit()
    
    await AuditService.log(
        db, action="VET_VISIT_RECORDED", resource="CASE_VISIT", resource_id=visit.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role
    )
    
    return {"message": "Visit logged successfully", "visit_id": visit.id}
