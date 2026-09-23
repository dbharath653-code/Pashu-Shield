"""Data-derived spatial-temporal outbreak clustering.

Input: disease reports (farmer/vet), verified lab results, and government surveillance
observations persisted in the database, within a time window.
Method: per-disease density clustering (DBSCAN-style with haversine eps) over records that
have real coordinates. Records without coordinates are counted per district but never placed
on the map at an invented location.
Output: cluster centroid, radius, case/death counts, time window, evidence level and the
contributing record ids. Evidence level is the *highest* verification present:
    REPORTED < UNDER_VERIFICATION < VETERINARIAN_VERIFIED < LAB_CONFIRMED
Clusters are decision support ("PREDICTED/REPORTED"), not official outbreak declarations.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import DiseaseReport, SurveillanceObservation
from backend.services.spatial import haversine_distance, valid_coordinates

EVIDENCE_ORDER = ["REPORTED", "UNDER_VERIFICATION", "VETERINARIAN_VERIFIED", "LAB_CONFIRMED"]


def _evidence_for_report(r: DiseaseReport) -> str:
    if r.verification_status == "LAB_CONFIRMED":
        return "LAB_CONFIRMED"
    if r.verification_status == "VERIFIED":
        return "VETERINARIAN_VERIFIED"
    if r.status in ("ASSIGNED", "VISIT_SCHEDULED", "VISITED", "SAMPLE_COLLECTED", "LAB_TESTING", "RESULT_AVAILABLE"):
        return "UNDER_VERIFICATION"
    return "REPORTED"


def _evidence_for_obs(o: SurveillanceObservation) -> str:
    return "LAB_CONFIRMED" if o.source_type == "LAB" else ("VETERINARIAN_VERIFIED" if o.verification_status == "VERIFIED" else "REPORTED")


async def load_points(db: AsyncSession, since: datetime, disease: Optional[str] = None, district: Optional[str] = None, include_demo: Optional[bool] = None) -> List[Dict[str, Any]]:
    include_demo = settings.DATA_MODE != "live" if include_demo is None else include_demo
    q = select(DiseaseReport).where(DiseaseReport.created_at >= since, DiseaseReport.deleted_at.is_(None), DiseaseReport.status != "CLOSED")
    if not include_demo:
        q = q.where(DiseaseReport.is_demo.is_(False))
    if disease:
        q = q.where(DiseaseReport.suspected_disease == disease)
    if district:
        q = q.where(DiseaseReport.district == district)
    points = [{
        "id": r.id, "kind": "REPORT", "disease": r.suspected_disease or "Unknown", "district": r.district, "lat": r.lat, "lng": r.lng,
        "cases": r.number_affected or 0, "deaths": r.number_dead or 0, "at": r.created_at, "evidence": _evidence_for_report(r),
        "source_type": r.source_type, "is_demo": r.is_demo,
    } for r in (await db.execute(q)).scalars().all()]
    oq = select(SurveillanceObservation).where(SurveillanceObservation.observed_at >= since)
    if not include_demo:
        oq = oq.where(SurveillanceObservation.is_demo.is_(False))
    if disease:
        oq = oq.where(SurveillanceObservation.disease == disease)
    if district:
        oq = oq.where(SurveillanceObservation.district == district)
    for o in (await db.execute(oq)).scalars().all():
        points.append({"id": o.id, "kind": "OBSERVATION", "disease": o.disease, "district": o.district, "lat": o.lat, "lng": o.lng,
                       "cases": o.case_count, "deaths": o.death_count, "at": o.observed_at, "evidence": _evidence_for_obs(o),
                       "source_type": o.source_type, "is_demo": o.is_demo})
    return points


def cluster_points(points: List[Dict[str, Any]], eps_km: float = 10.0, min_reports: int = 2) -> List[Dict[str, Any]]:
    clusters: List[Dict[str, Any]] = []
    by_disease: Dict[str, List[Dict[str, Any]]] = {}
    for p in points:
        if valid_coordinates(p["lat"], p["lng"]) and p["disease"] and p["disease"] != "Unknown":
            by_disease.setdefault(p["disease"], []).append(p)
    for disease, pts in by_disease.items():
        labels = [-1] * len(pts)
        cid = 0
        for i in range(len(pts)):
            if labels[i] != -1:
                continue
            neighbours = [j for j in range(len(pts)) if haversine_distance(pts[i]["lat"], pts[i]["lng"], pts[j]["lat"], pts[j]["lng"]) <= eps_km]
            if len(neighbours) < min_reports:
                continue
            labels[i] = cid
            queue = list(neighbours)
            while queue:
                j = queue.pop()
                if labels[j] == -1:
                    labels[j] = cid
                    nb = [k for k in range(len(pts)) if haversine_distance(pts[j]["lat"], pts[j]["lng"], pts[k]["lat"], pts[k]["lng"]) <= eps_km]
                    if len(nb) >= min_reports:
                        queue.extend(k for k in nb if labels[k] == -1)
            cid += 1
        for c in range(cid):
            members = [pts[i] for i in range(len(pts)) if labels[i] == c]
            lat = sum(m["lat"] for m in members) / len(members)
            lng = sum(m["lng"] for m in members) / len(members)
            radius = max(haversine_distance(lat, lng, m["lat"], m["lng"]) for m in members)
            evidence = max((m["evidence"] for m in members), key=EVIDENCE_ORDER.index)
            times = [m["at"] for m in members if m["at"]]
            districts = sorted({m["district"] for m in members if m["district"]})
            cases = sum(m["cases"] for m in members)
            verified_share = sum(1 for m in members if EVIDENCE_ORDER.index(m["evidence"]) >= 2) / len(members)
            clusters.append({
                "cluster_id": f"{disease[:12].upper().replace(' ', '')}-{round(lat, 3)}-{round(lng, 3)}",
                "disease": disease, "district": districts[0] if districts else None, "districts": districts,
                "lat": round(lat, 5), "lng": round(lng, 5), "radius_km": round(max(radius, 0.5), 2),
                "cases": cases, "deaths": sum(m["deaths"] for m in members), "record_count": len(members),
                "time_window": {"start": min(times).isoformat() if times else None, "end": max(times).isoformat() if times else None},
                "evidence_level": evidence,
                "confidence": round(min(0.95, 0.3 + 0.1 * len(members) + 0.4 * verified_share), 2),
                "contributing_records": [m["id"] for m in members][:50],
                "source_types": sorted({m["source_type"] for m in members if m["source_type"]}),
                "is_demo": any(m["is_demo"] for m in members),
                "risk_level": "High Risk" if evidence in ("LAB_CONFIRMED", "VETERINARIAN_VERIFIED") or cases >= 20 else "Moderate Risk",
                "latest_case": max(times).strftime("%Y-%m-%d") if times else None,
                "method": f"density clustering eps={eps_km}km min_records={min_reports}",
            })
    clusters.sort(key=lambda c: (-EVIDENCE_ORDER.index(c["evidence_level"]), -c["cases"]))
    return clusters


async def detect_clusters(db: AsyncSession, days: int = 21, disease: Optional[str] = None, district: Optional[str] = None, eps_km: float = 10.0, min_reports: int = 2) -> Dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=days)
    points = await load_points(db, since, disease, district)
    located = sum(1 for p in points if valid_coordinates(p["lat"], p["lng"]))
    return {
        "clusters": cluster_points(points, eps_km, min_reports),
        "input_records": len(points), "records_with_coordinates": located, "records_without_coordinates": len(points) - located,
        "window_days": days, "generated_at": datetime.utcnow().isoformat(), "source": "backend",
        "data_mode": settings.DATA_MODE,
        "label": "DATA-DERIVED CLUSTERS — decision support, not an official outbreak declaration",
    }
