"""Veterinary dispatch.

Pipeline: eligible vets (role, active, verified) -> jurisdiction/spatial filter ->
availability -> skill match -> distance -> workload -> ranked dispatch request ->
accept / reject / timeout -> automatic re-offer to the next candidate.

No coordinates are invented. A vet without a recent GPS fix is still eligible within their
district but is ranked with `distance_basis = LOCATION_UNAVAILABLE` and no distance value.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import DispatchRequest, User, UserRole, VeterinarianProfile, VeterinaryCase
from backend.services.spatial import haversine_distance, valid_coordinates, vets_within

# Backwards-compatible import location for existing callers.
__all__ = ["DispatchEngine", "haversine_distance"]

ACTIVE_CASE_STATES = ("ASSIGNED", "ACCEPTED", "EN_ROUTE", "ON_SITE", "UNDER_EXAMINATION", "TREATMENT", "LAB_REQUIRED")
LOCATION_STALE_AFTER = timedelta(hours=2)


class DispatchEngine:
    @classmethod
    async def find_eligible_veterinarians(
        cls,
        db: AsyncSession,
        district: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        max_distance_km: float = 60.0,
        species: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        exclude = set(exclude_ids or [])
        vets = (await db.execute(select(User).where(
            User.role.in_([UserRole.VETERINARIAN.value, UserRole.PARA_VET.value]),
            User.is_active.is_(True),
            User.is_verified.is_(True),
        ))).scalars().all()
        if not vets:
            return []
        ids = [v.id for v in vets]
        profiles = {p.user_id: p for p in (await db.execute(select(VeterinarianProfile).where(VeterinarianProfile.user_id.in_(ids)))).scalars().all()}
        workloads = dict((await db.execute(
            select(VeterinaryCase.assigned_vet_id, func.count(VeterinaryCase.id))
            .where(VeterinaryCase.assigned_vet_id.in_(ids), VeterinaryCase.status.in_(ACTIVE_CASE_STATES))
            .group_by(VeterinaryCase.assigned_vet_id)
        )).all())

        spatial_hits: Dict[str, float] = {}
        engine = "NONE"
        if valid_coordinates(lat, lng):
            hits, engine = await vets_within(db, lat, lng, max_distance_km)
            spatial_hits = {h["user_id"]: h["distance_km"] for h in hits}

        now = datetime.utcnow()
        ranked: List[Dict[str, Any]] = []
        for vet in vets:
            if vet.id in exclude:
                continue
            profile = profiles.get(vet.id)
            availability = profile.availability_status if profile else "UNKNOWN"
            if availability in ("OFF_DUTY", "BUSY"):
                continue
            workload = int(workloads.get(vet.id, 0))
            max_cases = profile.max_active_cases if profile else 8
            if workload >= max_cases:
                continue

            same_district = (vet.district or "").lower() == (district or "").lower()
            fresh_fix = bool(profile and profile.last_location_update and now - profile.last_location_update <= LOCATION_STALE_AFTER and valid_coordinates(profile.current_lat, profile.current_lng))
            distance_km: Optional[float] = None
            basis = "LOCATION_UNAVAILABLE"
            if vet.id in spatial_hits and fresh_fix:
                distance_km = spatial_hits[vet.id]
                basis = "STRAIGHT_LINE"
                radius = profile.service_radius_km if profile else max_distance_km
                if distance_km > radius:
                    continue
            elif not same_district:
                continue  # outside district and not provably nearby

            specs = [s.lower() for s in ((profile.specializations if profile else None) or [])]
            skill_match = bool(species and any(species.lower() in s or s in species.lower() for s in specs))

            score = 0.0
            breakdown = {}
            breakdown["district"] = 30.0 if same_district else 0.0
            breakdown["distance"] = round(max(0.0, 40.0 * (1 - distance_km / max_distance_km)), 1) if distance_km is not None else 10.0
            breakdown["availability"] = 15.0 if availability == "AVAILABLE" else 5.0
            breakdown["skill"] = 10.0 if skill_match else 0.0
            breakdown["workload"] = round(-5.0 * workload, 1)
            score = sum(breakdown.values())

            ranked.append({
                "vet_id": vet.id,
                "full_name": vet.full_name,
                "license_number": vet.license_number,
                "qualification": vet.qualification,
                "specialization": vet.specialization,
                "phone": vet.phone,
                "email": vet.email,
                "district": vet.district,
                "distance_km": distance_km,
                "distance_basis": basis,
                "eta_status": "ETA_UNAVAILABLE",
                "availability_status": availability,
                "current_case_count": workload,
                "location_status": "GPS" if fresh_fix else "LOCATION_UNAVAILABLE",
                "rank_score": round(score, 1),
                "score_breakdown": breakdown,
                "is_same_district": same_district,
                "spatial_engine": engine,
            })
        ranked.sort(key=lambda x: (-x["rank_score"], x["distance_km"] if x["distance_km"] is not None else 1e9))
        return ranked

    @classmethod
    async def create_request(cls, db: AsyncSession, case: VeterinaryCase, candidate: Dict[str, Any], rank: int = 1) -> DispatchRequest:
        req = DispatchRequest(
            id=f"DSP-{uuid.uuid4().hex[:10].upper()}",
            case_id=case.id,
            vet_id=candidate["vet_id"],
            status="PENDING",
            rank=rank,
            distance_km=candidate.get("distance_km"),
            distance_basis=candidate.get("distance_basis"),
            eta_status="ETA_UNAVAILABLE",
            score_breakdown=candidate.get("score_breakdown", {}),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.DISPATCH_ACCEPT_TIMEOUT_MINUTES),
        )
        db.add(req)
        return req

    @classmethod
    async def previously_offered(cls, db: AsyncSession, case_id: str) -> List[str]:
        return list((await db.execute(select(DispatchRequest.vet_id).where(DispatchRequest.case_id == case_id))).scalars().all())

    @classmethod
    async def offer_next(cls, db: AsyncSession, case: VeterinaryCase, actor=None) -> Optional[Dict[str, Any]]:
        """Offer the case to the best candidate not yet tried. Returns candidate or None."""
        from backend.services.workflow import transition
        tried = await cls.previously_offered(db, case.id)
        candidates = await cls.find_eligible_veterinarians(db, case.district, case.lat, case.lng, species=case.species, exclude_ids=tried)
        if not candidates:
            case.assigned_vet_id = None
            if case.status != "TRIAGED":
                transition(db, "CASE", case, "TRIAGED", actor, note="No eligible veterinarian available; escalated for manual assignment")
            return None
        best = candidates[0]
        await cls.create_request(db, case, best, rank=len(tried) + 1)
        case.assigned_vet_id = best["vet_id"]
        case.assigned_at = datetime.utcnow()
        if case.status != "ASSIGNED":
            transition(db, "CASE", case, "ASSIGNED", actor, note=f"Dispatch offered to {best['vet_id']}")
        return best

    @classmethod
    async def expire_stale_requests(cls, db: AsyncSession) -> int:
        """Worker job: expire unanswered offers and re-offer to the next candidate."""
        now = datetime.utcnow()
        stale = (await db.execute(select(DispatchRequest).where(DispatchRequest.status == "PENDING", DispatchRequest.expires_at < now))).scalars().all()
        for req in stale:
            req.status = "EXPIRED"
            req.responded_at = now
            case = await db.get(VeterinaryCase, req.case_id)
            if case and case.status == "ASSIGNED" and case.assigned_vet_id == req.vet_id:
                await cls.offer_next(db, case)
        await db.commit()
        return len(stale)
