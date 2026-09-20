import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import LabSample, LabTest, Laboratory, User, UserRole, VeterinaryCase
from backend.schemas import SampleCreate, SampleStatusUpdate, TestResultUpdate, SampleVerificationRequest
from backend.security import get_current_user, require_roles
from backend.services.websocket_manager import ws_manager
from backend.services.notification_service import NotificationService
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/labs", tags=["Laboratory & Samples"])

@router.get("/samples")
async def get_samples(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LabSample).order_by(LabSample.created_at.desc())
    if district:
        stmt = stmt.where(LabSample.district == district)
    if status:
        stmt = stmt.where(LabSample.status == status)
    if priority:
        stmt = stmt.where(LabSample.priority == priority)
        
    samples = (await db.execute(stmt)).scalars().all()
    
    # Load associated tests
    result = []
    for s in samples:
        test_stmt = select(LabTest).where(LabTest.sample_id == s.id)
        tests = (await db.execute(test_stmt)).scalars().all()
        result.append({
            "id": s.id,
            "sampleCode": s.sample_code,
            "caseId": s.case_id,
            "animalId": s.animal_id or f"ANM-{s.id[-6:]}",
            "species": s.species,
            "diseaseSuspected": s.disease_suspected,
            "sampleType": s.sample_type,
            "priority": s.priority,
            "status": s.status,
            "collectionDate": s.collection_date.strftime("%Y-%m-%d"),
            "location": s.location or f"{s.district} Diagnostic Center",
            "district": s.district,
            "qrCode": s.qr_code,
            "syncStatus": "Synced",
            "tests": [
                {
                    "id": t.id,
                    "testName": t.test_name,
                    "status": t.status,
                    "result": t.result,
                    "value": t.value,
                    "remarks": t.remarks
                }
                for t in tests
            ],
            "verification": {
                "verifiedBy": s.verified_by_name or "Pending Verification",
                "date": s.verified_at.strftime("%Y-%m-%d") if s.verified_at else None,
                "remarks": s.verification_remarks or ""
            } if s.verified_at else None
        })
    return result

@router.post("/samples")
async def register_sample(
    req: SampleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sample_id = f"SMP-{uuid.uuid4().hex[:8].upper()}"
    sample_code = f"SMP-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    
    sample = LabSample(
        id=sample_id,
        sample_code=sample_code,
        case_id=req.case_id,
        animal_id=req.animal_id,
        collected_by_id=current_user.id,
        species=req.species,
        disease_suspected=req.disease_suspected,
        sample_type=req.sample_type,
        priority=req.priority,
        status="COLLECTED",
        collection_date=datetime.utcnow(),
        district=req.district,
        location=req.location or req.district,
        qr_code=f"PASHU:SAMPLE:{sample_code}",
        notes=req.notes
    )
    db.add(sample)
    
    # Create lab tests
    for test_name in (req.tests or ["RT-PCR"]):
        test = LabTest(
            id=f"TST-{uuid.uuid4().hex[:8].upper()}",
            sample_id=sample_id,
            test_name=test_name,
            status="Pending"
        )
        db.add(test)
        
    await db.commit()
    await db.refresh(sample)
    
    # Emit WebSocket event
    await ws_manager.broadcast({
        "type": "LAB_SAMPLE_COLLECTED",
        "sample": {
            "id": sample.id,
            "sampleCode": sample.sample_code,
            "diseaseSuspected": sample.disease_suspected,
            "priority": sample.priority,
            "district": sample.district
        }
    })
    
    await AuditService.log(
        db, action="SAMPLE_REGISTERED", resource="LAB_SAMPLE", resource_id=sample.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role
    )
    
    return {"message": "Sample registered successfully", "sample_id": sample.id, "sample_code": sample.sample_code}

@router.patch("/samples/{sample_id}/status")
async def update_sample_status(
    sample_id: str,
    req: SampleStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LabSample).where(LabSample.id == sample_id)
    sample = (await db.execute(stmt)).scalars().first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
        
    old_status = sample.status
    sample.status = req.status
    now = datetime.utcnow()
    
    if req.status in ["RECEIVED", "Received"]:
        sample.received_at = now
    elif req.status in ["TESTING", "Testing"]:
        sample.tested_at = now
        
    await db.commit()
    
    # WebSocket update
    await ws_manager.broadcast({
        "type": "SAMPLE_STATUS_CHANGED",
        "sample": {"id": sample.id, "status": sample.status, "updated_by": current_user.full_name}
    })
    
    await AuditService.log(
        db, action="SAMPLE_STATUS_CHANGED", resource="LAB_SAMPLE", resource_id=sample.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role,
        old_value={"status": old_status}, new_value={"status": sample.status}
    )
    
    return {"message": "Sample status updated", "status": sample.status}

@router.post("/samples/{sample_id}/verify")
async def verify_sample_result(
    sample_id: str,
    req: SampleVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value, UserRole.SYSTEM_ADMIN.value]))
):
    stmt = select(LabSample).where(LabSample.id == sample_id)
    sample = (await db.execute(stmt)).scalars().first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
        
    sample.status = "VERIFIED"
    sample.verified_at = datetime.utcnow()
    sample.verified_by_id = current_user.id
    sample.verified_by_name = current_user.full_name
    sample.verification_remarks = req.remarks
    
    await db.commit()
    
    # Broadcast verified result to Vet and Government surveillance
    await ws_manager.broadcast({
        "type": "LAB_RESULT_VERIFIED",
        "sample": {
            "id": sample.id,
            "sampleCode": sample.sample_code,
            "disease": sample.disease_suspected,
            "district": sample.district,
            "verified_by": current_user.full_name,
            "remarks": req.remarks
        }
    })
    
    await AuditService.log(
        db, action="LAB_RESULT_VERIFIED", resource="LAB_SAMPLE", resource_id=sample.id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role,
        new_value={"status": "VERIFIED", "remarks": req.remarks}
    )
    
    return {"message": "Lab result verified and released to surveillance system", "sample_id": sample.id}

@router.patch("/samples/{sample_id}/tests")
async def update_sample_test(
    sample_id: str,
    req: TestResultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LabTest).where(LabTest.id == req.test_id, LabTest.sample_id == sample_id)
    test = (await db.execute(stmt)).scalars().first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
        
    test.status = req.status
    test.result = req.result
    test.value = req.value
    test.remarks = req.remarks
    test.tested_by_id = current_user.id
    test.tested_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Test result recorded", "test_id": test.id, "result": test.result}
