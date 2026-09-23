"""Surveillance dashboard data. Every figure is computed from stored records; nothing is
floored, padded or hardcoded. Each block carries provenance (source, evidence level,
last updated) and demo records are excluded unless DATA_MODE permits them."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import (DataSourceStatus, DiseaseReport, ExternalDataRecord, LabSample, OutbreakEvent, SurveillanceObservation, User,
                            VaccinationRecord, VeterinaryCase)
from backend.security import Permission, require_permission, resolve_district_filter
from backend.services.districts import MAHARASHTRA_DISTRICTS

router = APIRouter(prefix="/surveillance", tags=["Maharashtra Disease Surveillance"])

OPEN_CASE = ("RESOLVED", "CLOSED", "REJECTED")


def _demo_filter(col):
    return True if settings.DATA_MODE != "live" else col.is_(False)


def _scoped(stmt, model, district):
    stmt = stmt.where(_demo_filter(model.is_demo))
    if district:
        stmt = stmt.where(model.district == district)
    return stmt


@router.get("/overview")
async def get_surveillance_overview(district: Optional[str] = None, db: AsyncSession = Depends(get_db),
                                    current_user: User = Depends(require_permission(Permission.SURVEILLANCE_VIEW))):
    d = resolve_district_filter(current_user, district)
    since = datetime.utcnow() - timedelta(days=30)
    q = lambda s, m: _scoped(s, m, d)  # noqa: E731
    reports_30d = (await db.execute(q(select(func.count(DiseaseReport.id)).where(DiseaseReport.created_at >= since, DiseaseReport.deleted_at.is_(None)), DiseaseReport))).scalar() or 0
    verified_30d = (await db.execute(q(select(func.count(DiseaseReport.id)).where(DiseaseReport.created_at >= since, DiseaseReport.verification_status.in_(["VERIFIED", "LAB_CONFIRMED"])), DiseaseReport))).scalar() or 0
    active_cases = (await db.execute(q(select(func.count(VeterinaryCase.id)).where(VeterinaryCase.status.notin_(OPEN_CASE), VeterinaryCase.deleted_at.is_(None)), VeterinaryCase))).scalar() or 0
    affected = (await db.execute(q(select(func.coalesce(func.sum(DiseaseReport.number_affected), 0)).where(DiseaseReport.created_at >= since), DiseaseReport))).scalar() or 0
    dead = (await db.execute(q(select(func.coalesce(func.sum(DiseaseReport.number_dead), 0)).where(DiseaseReport.created_at >= since), DiseaseReport))).scalar() or 0
    pending_lab = (await db.execute(q(select(func.count(LabSample.id)).where(LabSample.status.notin_(["VERIFIED", "RELEASED", "CLOSED", "REJECTED"])), LabSample))).scalar() or 0
    outbreaks = (await db.execute(q(select(func.count(OutbreakEvent.id)).where(OutbreakEvent.status == "Active"), OutbreakEvent))).scalar() or 0
    vacc_30d = (await db.execute(q(select(func.count(VaccinationRecord.id)).where(VaccinationRecord.vaccination_date >= since), VaccinationRecord))).scalar() or 0
    gov_obs = (await db.execute(q(select(func.coalesce(func.sum(SurveillanceObservation.case_count), 0)).where(SurveillanceObservation.source_type == "GOVERNMENT", SurveillanceObservation.observed_at >= since), SurveillanceObservation))).scalar()
    gov_status = await db.get(DataSourceStatus, "GOVT_SURVEILLANCE")
    census = (await db.execute(select(ExternalDataRecord).where(ExternalDataRecord.provider == "DAHD_CENSUS", ExternalDataRecord.external_id == "__state__").order_by(ExternalDataRecord.retrieved_at.desc()).limit(1))).scalars().first()
    platform = "PLATFORM_RECORDS (field reports; mostly unverified)"
    kpis = [
        {"label": "Reports (30 days)", "value": reports_30d, "provenance": platform, "evidence": "REPORTED", "status": "warning" if reports_30d else "neutral"},
        {"label": "Verified / Lab-confirmed Reports (30 days)", "value": verified_30d, "provenance": "PLATFORM_RECORDS", "evidence": "VETERINARIAN_VERIFIED+", "status": "danger" if verified_30d else "neutral"},
        {"label": "Active Veterinary Cases", "value": active_cases, "provenance": "PLATFORM_RECORDS", "status": "neutral"},
        {"label": "Active Outbreak Events", "value": outbreaks, "provenance": "PLATFORM_RECORDS (officer-declared)", "status": "danger" if outbreaks else "success"},
        {"label": "Animals Affected (30 days, reported)", "value": int(affected), "provenance": platform, "evidence": "REPORTED", "status": "danger" if affected else "neutral"},
        {"label": "Reported Mortality (30 days)", "value": int(dead), "provenance": platform, "evidence": "REPORTED", "status": "danger" if dead else "neutral"},
        {"label": "Pending Lab Samples", "value": pending_lab, "provenance": "PLATFORM_RECORDS", "status": "warning" if pending_lab else "neutral"},
        {"label": "Vaccinations Recorded (30 days)", "value": vacc_30d, "provenance": "PLATFORM_RECORDS", "status": "success"},
        {"label": "Government-reported Cases (30 days)", "value": int(gov_obs) if gov_status and gov_status.state == "LIVE" else None,
         "provenance": f"GOVERNMENT FEED — {gov_status.state if gov_status else 'CONFIGURATION_REQUIRED'}", "status": "neutral"},
        {"label": "Total Livestock Population", "value": (census.payload or {}).get("total_livestock") if census else None,
         "provenance": f"HISTORICAL (DAHD Livestock Census {(census.payload or {}).get('reference_year')})" if census else "NOT_IMPORTED", "status": "neutral"},
    ]
    sources = (await db.execute(select(DataSourceStatus))).scalars().all()
    return {"kpis": kpis, "meta": {
        "state": "Maharashtra", "district": d, "window_days": 30, "last_updated": datetime.utcnow().isoformat(),
        "data_mode": settings.DATA_MODE, "includes_demo_data": settings.DATA_MODE != "live",
        "data_sources": [{"name": "Pashu-Shield field reports", "status": "LIVE"}] + [{"name": s.provider, "status": s.state, "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None} for s in sources],
    }}


@router.get("/districts")
async def get_district_surveillance(days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db),
                                    current_user: User = Depends(require_permission(Permission.SURVEILLANCE_VIEW))):
    scope_d = resolve_district_filter(current_user, None)
    since = datetime.utcnow() - timedelta(days=days)
    prev = since - timedelta(days=days)
    def agg(start, end):  # noqa: E306
        return (select(DiseaseReport.district, func.count(DiseaseReport.id), func.coalesce(func.sum(DiseaseReport.number_affected), 0),
                       func.coalesce(func.sum(DiseaseReport.number_dead), 0),
                       func.sum(case((DiseaseReport.verification_status.in_(["VERIFIED", "LAB_CONFIRMED"]), 1), else_=0)))
                .where(DiseaseReport.created_at >= start, DiseaseReport.created_at < end, DiseaseReport.deleted_at.is_(None), _demo_filter(DiseaseReport.is_demo))
                .group_by(DiseaseReport.district))
    now = datetime.utcnow()
    cur = {r[0]: r for r in (await db.execute(agg(since, now))).all()}
    old = {r[0]: r for r in (await db.execute(agg(prev, since))).all()}
    active = dict((await db.execute(select(VeterinaryCase.district, func.count(VeterinaryCase.id)).where(VeterinaryCase.status.notin_(OPEN_CASE), _demo_filter(VeterinaryCase.is_demo)).group_by(VeterinaryCase.district))).all())
    out = []
    for dref in MAHARASHTRA_DISTRICTS:
        name = dref["name"]
        if scope_d and name.lower() != scope_d.lower():
            continue
        c = cur.get(name)
        reports, affected, dead, verified = (c[1], int(c[2]), int(c[3]), int(c[4] or 0)) if c else (0, 0, 0, 0)
        prev_reports = old[name][1] if name in old else 0
        trend = "insufficient_data" if reports + prev_reports < 3 else ("up" if reports > prev_reports * 1.2 else ("down" if reports < prev_reports * 0.8 else "flat"))
        risk = "HIGH" if verified >= 3 or dead >= 5 else ("MEDIUM" if reports >= 5 or verified >= 1 else ("LOW" if reports else "NO_REPORTS"))
        out.append({"district": name, "division": dref["division"], "totalCases": affected, "reports": reports, "verifiedReports": verified,
                    "activeCases": active.get(name, 0), "recovered": None, "mortality": dead, "vaccinationCoverage": None,
                    "riskLevel": risk, "riskBasis": "rule: verified>=3 or deaths>=5 → HIGH; reports>=5 or any verified → MEDIUM",
                    "trend": trend, "lat": dref["lat"], "lng": dref["lng"], "provenance": "PLATFORM_RECORDS", "window_days": days})
    return out


@router.get("/trends")
async def get_trends(days: int = Query(21, ge=7, le=180), district: Optional[str] = None, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_permission(Permission.SURVEILLANCE_VIEW))):
    d = resolve_district_filter(current_user, district)
    since = (datetime.utcnow() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(DiseaseReport.created_at, DiseaseReport.number_affected, DiseaseReport.number_dead).where(DiseaseReport.created_at >= since, DiseaseReport.deleted_at.is_(None), _demo_filter(DiseaseReport.is_demo))
    if d:
        stmt = stmt.where(DiseaseReport.district == d)
    buckets = {(since + timedelta(days=i)).date(): {"cases": 0, "deaths": 0, "reports": 0} for i in range(days)}
    for created, aff, dead in (await db.execute(stmt)).all():
        b = buckets.get(created.date())
        if b:
            b["cases"] += aff or 0
            b["deaths"] += dead or 0
            b["reports"] += 1
    # `recovered` is not tracked per day; returned as null rather than invented.
    return [{"date": k.strftime("%d %b"), "isoDate": k.isoformat(), **v, "recovered": None, "provenance": "PLATFORM_RECORDS"} for k, v in sorted(buckets.items())]
