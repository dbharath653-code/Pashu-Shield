import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import DataSourceStatus, ExternalDataRecord, User
from backend.security import Permission, require_permission
from backend.services.audit_service import AuditService
from backend.services.districts import DISTRICT_NAMES
from backend.services.external_data_service import census_provider, government_provider, nadres_provider, weather_provider
from backend.services.notification_service import NotificationService, verify_whatsapp_signature

router = APIRouter(prefix="/external", tags=["External Data Adapters (NADRES / DAHD / Weather)"])

KNOWN_PROVIDERS = [
    ("NADRES", "surveillance", nadres_provider.configured()), ("GOVT_SURVEILLANCE", "surveillance", government_provider.configured()),
    ("DAHD_CENSUS", "reference", True), ("WEATHER_OPEN_METEO", "weather", weather_provider.configured()),
]


@router.get("/nadres/bulletin")
async def get_nadres_bulletin(state: str = Query("Maharashtra", max_length=64), current_user: User = Depends(require_permission(Permission.DATA_SOURCE_VIEW))):
    return await nadres_provider.fetch_disease_forewarning(state=state)


@router.get("/census/district")
async def get_census_data(district: str = Query("Pune", max_length=128), current_user: User = Depends(require_permission(Permission.SURVEILLANCE_VIEW))):
    return await census_provider.get_district_census(district=district)


@router.get("/weather")
async def get_weather(lat: float = Query(18.5204, ge=-90, le=90), lng: float = Query(73.8567, ge=-180, le=180),
                      current_user: User = Depends(require_permission(Permission.SURVEILLANCE_VIEW))):
    return await weather_provider.get_district_weather(lat=lat, lng=lng)


@router.get("/data-sources")
async def data_sources(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.DATA_SOURCE_VIEW))):
    """Admin data-source health: configured?, state, last success/failure, latency, record count."""
    rows = {r.provider: r for r in (await db.execute(select(DataSourceStatus))).scalars().all()}
    out = []
    names = {p for p, _, _ in KNOWN_PROVIDERS} | set(rows)
    for name in sorted(names):
        r = rows.get(name)
        configured = next((c for p, _, c in KNOWN_PROVIDERS if p == name), r.configured if r else False)
        out.append({"provider": name, "category": r.category if r else next((c for p, c, _ in KNOWN_PROVIDERS if p == name), "external"),
                    "configured": configured, "state": (r.state if r else ("CONFIGURATION_REQUIRED" if not configured else "NOT_YET_CONTACTED")),
                    "last_success_at": r.last_success_at.isoformat() if r and r.last_success_at else None,
                    "last_failure_at": r.last_failure_at.isoformat() if r and r.last_failure_at else None,
                    "last_error": r.last_error if r else None, "last_latency_ms": r.last_latency_ms if r else None,
                    "records_received": r.records_received if r else 0})
    return {"environment": settings.ENVIRONMENT, "data_mode": settings.DATA_MODE, "sources": out}


class CensusRow(BaseModel):
    district: str = Field(min_length=2, max_length=128)
    cattle: Optional[int] = Field(default=None, ge=0)
    buffalo: Optional[int] = Field(default=None, ge=0)
    sheep: Optional[int] = Field(default=None, ge=0)
    goat: Optional[int] = Field(default=None, ge=0)
    pig: Optional[int] = Field(default=None, ge=0)
    poultry: Optional[int] = Field(default=None, ge=0)


class CensusImport(BaseModel):
    reference_year: int = Field(ge=1950, le=2100)
    source_citation: str = Field(min_length=10, max_length=500, description="Exact publication / table the figures were copied from")
    rows: List[CensusRow] = Field(min_length=1, max_length=100)


@router.post("/ingest/census")
async def ingest_census(req: CensusImport, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.DATA_INGEST))):
    """Import official DAHD Livestock Census district figures. Rows with unknown district names
    are rejected (not guessed). Stored as HISTORICAL reference data with citation."""
    accepted, rejected = 0, []
    state_total = 0
    for row in req.rows:
        canonical = DISTRICT_NAMES.get(row.district.strip().lower())
        if not canonical:
            rejected.append(row.district)
            continue
        payload = {**row.model_dump(), "district": canonical, "reference_year": req.reference_year, "source_citation": req.source_citation}
        payload["total_livestock"] = sum(v for k, v in row.model_dump().items() if k != "district" and k != "poultry" and v)
        state_total += payload["total_livestock"]
        db.add(ExternalDataRecord(id=uuid.uuid4().hex, provider="DAHD_CENSUS", external_id=canonical.lower(), source=req.source_citation, record_type="district_census",
                                  payload=payload, data_status="HISTORICAL", source_timestamp=datetime(req.reference_year, 1, 1), request_id=getattr(request.state, "request_id", None)))
        accepted += 1
    if accepted:
        db.add(ExternalDataRecord(id=uuid.uuid4().hex, provider="DAHD_CENSUS", external_id="__state__", source=req.source_citation, record_type="state_census",
                                  payload={"total_livestock": state_total, "reference_year": req.reference_year, "districts": accepted, "complete": accepted >= 36},
                                  data_status="HISTORICAL", source_timestamp=datetime(req.reference_year, 1, 1)))
    await AuditService.for_user(db, current_user, "CENSUS_IMPORTED", "EXTERNAL_DATA", "DAHD_CENSUS", request=request, commit=False,
                                new_value={"accepted": accepted, "rejected": rejected, "year": req.reference_year})
    await db.commit()
    return {"accepted": accepted, "rejected_districts": rejected}


@router.post("/ingest/{provider}")
async def trigger_ingest(provider: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.DATA_INGEST))):
    from backend.services.jobs import enqueue
    job_type = {"nadres": "ingest.nadres", "government": "ingest.government"}.get(provider.lower())
    if not job_type:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_PROVIDER", "message": "Unknown provider"})
    job = await enqueue(db, job_type, {"requested_by": current_user.id})
    await db.commit()
    return {"queued": True, "job_id": job.id}


# ---- Provider webhooks (no user auth; authenticated by provider signature) ---------------
webhooks = APIRouter(prefix="/webhooks", tags=["Provider Webhooks"])


@webhooks.get("/whatsapp")
async def whatsapp_verify(hub_mode: str = Query(None, alias="hub.mode"), hub_verify_token: str = Query(None, alias="hub.verify_token"),
                          hub_challenge: str = Query(None, alias="hub.challenge")):
    if settings.WHATSAPP_VERIFY_TOKEN and hub_mode == "subscribe" and hmac.compare_digest(hub_verify_token or "", settings.WHATSAPP_VERIFY_TOKEN):
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Verification failed"})


@webhooks.post("/whatsapp")
async def whatsapp_status(request: Request, db: AsyncSession = Depends(get_db)):
    raw = await request.body()
    if not verify_whatsapp_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=401, detail={"code": "INVALID_SIGNATURE", "message": "Invalid signature"})
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "BAD_PAYLOAD", "message": "Invalid JSON"})
    updated = 0
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            for st in (change.get("value") or {}).get("statuses", []) or []:
                err = (st.get("errors") or [{}])[0].get("title") if st.get("errors") else None
                if await NotificationService.apply_status_callback(db, st.get("id", ""), st.get("status", ""), err):
                    updated += 1
    return {"updated": updated}


@webhooks.post("/ivr")
async def ivr_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """IVR provider callback. Requires HMAC-SHA256 of the raw body in X-Signature using
    IVR_WEBHOOK_SECRET. No IVR provider is configured by default (returns 503)."""
    if settings.IVR_PROVIDER == "none" or not settings.IVR_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail={"code": "IVR_NOT_CONFIGURED", "message": "IVR provider not configured"})
    raw = await request.body()
    expected = hmac.new(settings.IVR_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("x-signature", "")):
        raise HTTPException(status_code=401, detail={"code": "INVALID_SIGNATURE", "message": "Invalid signature"})
    body = json.loads(raw or b"{}")
    from backend.services.audit_service import AuditService as A
    await A.log(db, "IVR_CALLBACK", "IVR", body.get("call_id"), new_value={"keys": sorted(body.keys())})
    # Mapping IVR keypad/speech input to a report requires the provider's documented schema;
    # the callback is recorded for follow-up by a call-centre operator.
    return {"received": True, "action": "RECORDED_FOR_OPERATOR_FOLLOW_UP"}
