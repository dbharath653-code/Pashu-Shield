import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import DiseaseReport, VeterinaryCase, Alert, User, UserRole
from backend.schemas import DiseaseReportCreate
from backend.security import get_current_user, get_current_user_optional
from backend.services.triage_service import TriageEngine
from backend.services.dispatch_service import DispatchEngine
from backend.services.websocket_manager import ws_manager
from backend.services.notification_service import NotificationService
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/reports", tags=["Disease Reports & Triage"])

@router.get("")
async def get_reports(
    district: Optional[str] = None,
    species: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    stmt = select(DiseaseReport).order_by(DiseaseReport.created_at.desc())
    
    if current_user and current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(DiseaseReport.user_id == current_user.id)
    elif district:
        stmt = stmt.where(DiseaseReport.district == district)
        
    if species:
        stmt = stmt.where(DiseaseReport.species == species)
    if status:
        stmt = stmt.where(DiseaseReport.status == status)
        
    result = await db.execute(stmt)
    reports = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "reportNumber": r.report_number,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "species": r.species,
            "numberAffected": r.number_affected,
            "numberDead": r.number_dead,
            "district": r.district,
            "taluka": r.taluka,
            "village": r.village,
            "symptoms": r.symptoms or [],
            "status": r.status,
            "disease": r.suspected_disease,
            "triageRiskLevel": r.triage_risk_level,
            "triageUrgency": r.triage_urgency,
            "triageRecommendations": r.triage_recommendations,
            "source": r.source
        }
        for r in reports
    ]

@router.post("")
async def submit_disease_report(
    req: DiseaseReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # 1. Clinical Triage Evaluation
    triage = TriageEngine.evaluate(
        species=req.species,
        symptoms=req.symptoms,
        number_affected=req.number_affected,
        number_dead=req.number_dead,
        temperature=req.temperature,
        district=req.district
    )
    
    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    report_num = f"MH-{req.district[:3].upper()}-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    
    user_id = current_user.id if current_user else f"ANON-{uuid.uuid4().hex[:6]}"
    reporter_name = current_user.full_name if current_user else "Field Reporter"
    reporter_role = current_user.role if current_user else "FARMER"
    
    report = DiseaseReport(
        id=report_id,
        report_number=report_num,
        user_id=user_id,
        reporter_name=reporter_name,
        reporter_role=reporter_role,
        species=req.species,
        number_affected=req.number_affected,
        number_dead=req.number_dead,
        symptoms=req.symptoms,
        temperature=req.temperature,
        district=req.district,
        taluka=req.taluka or "Taluka-1",
        village=req.village,
        lat=req.lat or 18.5204,
        lng=req.lng or 73.8567,
        suspected_disease=req.suspected_disease or "Unknown",
        status="Suspected",
        triage_urgency=triage["urgency"],
        triage_risk_level=triage["risk_level"],
        triage_recommendations=triage["recommendations"],
        notes=req.notes,
        source="LIVE"
    )
    db.add(report)
    
    # 2. Automatically dispatch case if triage indicates veterinary evaluation is required
    created_case = None
    assigned_vet = None
    if triage["requires_veterinary_dispatch"] or req.number_dead > 0 or triage["risk_level"] in ["HIGH", "CRITICAL"]:
        eligible_vets = await DispatchEngine.find_eligible_veterinarians(
            db, district=req.district, lat=req.lat, lng=req.lng
        )
        assigned_vet_id = eligible_vets[0]["vet_id"] if eligible_vets else None
        if eligible_vets:
            assigned_vet = eligible_vets[0]

        case_id = f"VET-{uuid.uuid4().hex[:8].upper()}"
        case_num = f"CAS-{req.district[:3].upper()}-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        created_case = VeterinaryCase(
            id=case_id,
            case_number=case_num,
            report_id=report.id,
            farmer_id=user_id,
            assigned_vet_id=assigned_vet_id,
            status="ASSIGNED" if assigned_vet_id else "REPORTED",
            priority=triage["risk_level"],
            species=req.species,
            district=req.district,
            village=req.village,
            lat=req.lat or 18.5204,
            lng=req.lng or 73.8567,
            reported_problem=f"{len(req.symptoms)} symptoms reported: {', '.join(req.symptoms)}",
            risk_score=85.0 if triage["risk_level"] == "CRITICAL" else (65.0 if triage["risk_level"] == "HIGH" else 40.0),
            assigned_at=datetime.utcnow() if assigned_vet_id else None
        )
        db.add(created_case)

    # 3. Create high priority system alert if critical
    if triage["risk_level"] in ["HIGH", "CRITICAL"]:
        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        alert = Alert(
            id=alert_id,
            alert_code=f"ALR-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
            type="high" if triage["risk_level"] == "CRITICAL" else "warning",
            severity=triage["risk_level"],
            title=f"{triage['risk_level']} Risk Alert - {req.district} - {req.suspected_disease or 'Syndromic Disease'}",
            message=f"{req.number_affected} {req.species} affected ({req.number_dead} deaths) in village {req.village}, {req.district}.",
            district=req.district,
            taluka=req.taluka,
            disease=req.suspected_disease,
            is_broadcast=True
        )
        db.add(alert)
        
    await db.commit()
    await db.refresh(report)

    # 4. Trigger Real-time WebSocket Broadcast
    await ws_manager.broadcast({
        "type": "REPORT_CREATED",
        "report": {
            "id": report.id,
            "reportNumber": report.report_number,
            "species": report.species,
            "district": report.district,
            "village": report.village,
            "riskLevel": report.triage_risk_level,
            "disease": report.suspected_disease,
            "created_at": report.created_at.isoformat()
        }
    })
    
    if created_case:
        await ws_manager.broadcast({
            "type": "CASE_CREATED",
            "case": {
                "id": created_case.id,
                "caseNumber": created_case.case_number,
                "district": created_case.district,
                "village": created_case.village,
                "status": created_case.status,
                "assignedVetId": created_case.assigned_vet_id,
                "assignedVetName": assigned_vet["full_name"] if assigned_vet else "Pending Assignment"
            }
        })
        
        # Notify Veterinarian via SMS / WhatsApp adapter
        if assigned_vet and assigned_vet.get("phone"):
            await NotificationService.dispatch(
                channel="SMS",
                recipient=assigned_vet["phone"],
                template_name="VETERINARIAN_ASSIGNED",
                context={
                    "vet_name": assigned_vet["full_name"],
                    "case_number": created_case.case_number,
                    "vet_phone": assigned_vet.get("phone", "1962")
                }
            )

    await AuditService.log(
        db, action="DISEASE_REPORT_SUBMITTED", resource="REPORT", resource_id=report.id,
        user_id=user_id, user_name=reporter_name, role=reporter_role,
        new_value={"district": report.district, "species": report.species, "triage": triage["risk_level"]}
    )

    return {
        "success": True,
        "report": {
            "id": report.id,
            "reportNumber": report.report_number,
            "status": report.status,
            "district": report.district,
            "village": report.village,
            "species": report.species
        },
        "triage": triage,
        "assignedCase": {
            "caseId": created_case.id,
            "caseNumber": created_case.case_number,
            "status": created_case.status,
            "assignedVet": assigned_vet
        } if created_case else None
    }
