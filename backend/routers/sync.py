import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import (
    SyncEvent, Animal, Herd, DiseaseReport, VeterinaryCase,
    LabSample, VaccinationRecord, User
)
from backend.schemas import SyncPushRequest
from backend.security import get_current_user_optional
from backend.services.websocket_manager import ws_manager

router = APIRouter(prefix="/sync", tags=["Offline-First Synchronization"])

@router.post("/push")
async def sync_push(
    req: SyncPushRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Processes client sync queue with idempotency keys and duplicate prevention.
    Applies updates to primary SQL storage and returns processed status.
    """
    user_id = current_user.id if current_user else "ANONYMOUS-OFFLINE-USER"
    processed_items = []
    
    for item in req.items:
        # Check idempotency key to prevent double submission
        stmt = select(SyncEvent).where(SyncEvent.idempotency_key == item.idempotency_key)
        existing_event = (await db.execute(stmt)).scalars().first()
        
        if existing_event:
            # Already synced successfully
            processed_items.append({
                "localId": item.id,
                "idempotencyKey": item.idempotency_key,
                "status": "ALREADY_SYNCED",
                "message": "Duplicate avoided via idempotency key"
            })
            continue

        store = item.store
        data = item.data
        
        # Apply to database based on store
        try:
            if store == "animals":
                animal = Animal(
                    id=data.get("id") or str(uuid.uuid4()),
                    tag_id=data.get("tagId", "TAG-OFFLINE"),
                    species=data.get("species", "Cattle"),
                    breed=data.get("breed"),
                    sex=data.get("sex", "Female"),
                    age_years=float(data.get("age", 2.0)),
                    owner_id=user_id,
                    village=data.get("village", "Unknown"),
                    district=data.get("district", "Pune"),
                    health_status=data.get("healthStatus", "Healthy"),
                    risk_score=float(data.get("riskScore", 0.0))
                )
                db.add(animal)
                
            elif store == "herds":
                herd = Herd(
                    id=data.get("id") or str(uuid.uuid4()),
                    species=data.get("species", "Cattle"),
                    total_animals=int(data.get("totalAnimals", 1)),
                    owner_id=user_id,
                    village=data.get("village", "Unknown"),
                    district=data.get("district", "Pune"),
                    health_status=data.get("healthStatus", "Healthy")
                )
                db.add(herd)
                
            elif store == "reports" or store == "health_records":
                report = DiseaseReport(
                    id=data.get("id") or str(uuid.uuid4()),
                    report_number=f"MH-OFFLINE-{uuid.uuid4().hex[:6].upper()}",
                    user_id=user_id,
                    species=data.get("species", "Cattle"),
                    number_affected=int(data.get("numberAffected", 1)),
                    number_dead=int(data.get("numberDead", 0)),
                    symptoms=data.get("symptoms", []),
                    district=data.get("district", "Pune"),
                    village=data.get("village", "Unknown"),
                    suspected_disease=data.get("disease", "Unknown"),
                    source="OFFLINE_SYNC"
                )
                db.add(report)

            # Record sync event
            sync_ev = SyncEvent(
                id=str(uuid.uuid4()),
                user_id=user_id,
                client_sync_id=item.id,
                idempotency_key=item.idempotency_key,
                entity_type=store,
                entity_id=item.id,
                operation=item.operation,
                status="PROCESSED"
            )
            db.add(sync_ev)
            
            processed_items.append({
                "localId": item.id,
                "idempotencyKey": item.idempotency_key,
                "status": "SYNCED",
                "message": "Successfully synchronized"
            })
        except Exception as e:
            processed_items.append({
                "localId": item.id,
                "idempotencyKey": item.idempotency_key,
                "status": "ERROR",
                "error": str(e)
            })

    await db.commit()
    
    # Notify connected clients of fresh synchronization
    await ws_manager.broadcast({
        "type": "SYNC_COMPLETED",
        "user_id": user_id,
        "items_synced": len([i for i in processed_items if i["status"] == "SYNCED"])
    })
    
    return {
        "success": True,
        "synced_at": datetime.utcnow().isoformat(),
        "processed": processed_items
    }

@router.get("/pull")
async def sync_pull(since: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Pulls current database changes so client can refresh IndexedDB cache."""
    animals_stmt = select(Animal).limit(100)
    animals = (await db.execute(animals_stmt)).scalars().all()
    
    cases_stmt = select(VeterinaryCase).limit(100)
    cases = (await db.execute(cases_stmt)).scalars().all()
    
    samples_stmt = select(LabSample).limit(100)
    samples = (await db.execute(samples_stmt)).scalars().all()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "animals": [{"id": a.id, "tagId": a.tag_id, "species": a.species, "healthStatus": a.health_status, "district": a.district} for a in animals],
        "vetCases": [{"id": c.id, "species": c.species, "status": c.status, "district": c.district} for c in cases],
        "labSamples": [{"id": s.id, "status": s.status, "sampleType": s.sample_type, "disease": s.disease_suspected} for s in samples]
    }
