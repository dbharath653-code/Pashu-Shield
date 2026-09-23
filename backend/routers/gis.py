"""GIS layers built from stored records only. Hardcoded clusters/facilities were removed:
clusters come from outbreak_service (evidence-labelled), facilities and labs from their
tables. Routes come from the routing provider (OSRM) or report ETA_UNAVAILABLE."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import DiseaseReport, Laboratory, User, VeterinaryFacility
from backend.security import Permission, require_permission, resolve_district_filter
from backend.services import routing_service
from backend.services.outbreak_service import detect_clusters
from backend.services.spatial import parse_bbox, valid_coordinates

router = APIRouter(prefix="/gis", tags=["GIS & Spatial Layers"])

_RISK_LABEL = {"LAB_CONFIRMED": "Confirmed", "VETERINARIAN_VERIFIED": "High Risk", "UNDER_VERIFICATION": "Moderate Risk", "REPORTED": "Reported (unverified)"}


@router.get("/layers")
async def get_gis_layers(district: Optional[str] = None, bbox: Optional[str] = Query(None, description="minLng,minLat,maxLng,maxLat"),
                         days: int = Query(21, ge=1, le=180), db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(require_permission(Permission.GIS_VIEW))):
    d = resolve_district_filter(current_user, district)
    box = parse_bbox(bbox)
    detected = await detect_clusters(db, days=days, district=d)
    clusters = []
    for c in detected["clusters"]:
        if box and not (box[0] <= c["lng"] <= box[2] and box[1] <= c["lat"] <= box[3]):
            continue
        clusters.append({**c, "name": f"{c['disease']} cluster – {c['district']}", "risk_level": _RISK_LABEL.get(c["evidence_level"], c["evidence_level"])})
    fac_stmt = select(VeterinaryFacility)
    lab_stmt = select(Laboratory)
    if d:
        fac_stmt, lab_stmt = fac_stmt.where(VeterinaryFacility.district == d), lab_stmt.where(Laboratory.district == d)
    facilities = (await db.execute(fac_stmt)).scalars().all()
    labs = (await db.execute(lab_stmt)).scalars().all()

    def in_box(lat, lng):
        return valid_coordinates(lat, lng) and (not box or (box[0] <= lng <= box[2] and box[1] <= lat <= box[3]))

    return {
        "outbreak_clusters": clusters,
        "veterinary_facilities": [{"id": f.id, "name": f.name, "type": f.facility_type, "district": f.district, "lat": f.lat, "lng": f.lng,
                                   "mvu_available": f.mvu_available, "source": f.source, "isDemo": f.is_demo}
                                  for f in facilities if in_box(f.lat, f.lng)],
        "laboratories": [{"id": lab.id, "name": lab.name, "district": lab.district, "lat": lab.lat, "lng": lab.lng, "status": lab.status, "isDemo": lab.is_demo}
                         for lab in labs if in_box(lab.lat, lab.lng)],
        "meta": {"cluster_method": "density (haversine, eps 10 km, ≥2 reports)", "window_days": days, "data_mode": settings.DATA_MODE,
                 "records_without_coordinates": detected["records_without_coordinates"],
                 "facilities_source": "facility registry table (empty until imported)"},
    }


@router.get("/reports")
async def report_points(bbox: Optional[str] = None, district: Optional[str] = None, days: int = Query(30, ge=1, le=365), limit: int = Query(2000, le=5000),
                        db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.GIS_VIEW))):
    from datetime import datetime, timedelta
    d = resolve_district_filter(current_user, district)
    stmt = select(DiseaseReport).where(DiseaseReport.lat.isnot(None), DiseaseReport.created_at >= datetime.utcnow() - timedelta(days=days), DiseaseReport.deleted_at.is_(None))
    if settings.DATA_MODE == "live":
        stmt = stmt.where(DiseaseReport.is_demo.is_(False))
    if d:
        stmt = stmt.where(DiseaseReport.district == d)
    box = parse_bbox(bbox)
    if box:
        stmt = stmt.where(DiseaseReport.lng.between(box[0], box[2]), DiseaseReport.lat.between(box[1], box[3]))
    rows = (await db.execute(stmt.limit(limit))).scalars().all()
    from backend.services.report_service import evidence_label
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [r.lng, r.lat]},
         "properties": {"id": r.id, "disease": r.suspected_disease, "species": r.species, "risk": r.triage_risk_level, "evidence": evidence_label(r),
                        "locationStatus": r.location_status, "createdAt": r.created_at.isoformat()}} for r in rows]}


@router.get("/route")
async def calculate_route(start_lat: float = Query(ge=-90, le=90), start_lng: float = Query(ge=-180, le=180),
                          dest_lat: float = Query(ge=-90, le=90), dest_lng: float = Query(ge=-180, le=180),
                          current_user: User = Depends(require_permission(Permission.GIS_VIEW))):
    """Road route via the configured routing provider. Without one, returns straight-line
    distance labelled STRAIGHT_LINE and eta_status ETA_UNAVAILABLE (no invented travel time)."""
    r = await routing_service.route(start_lat, start_lng, dest_lat, dest_lng)
    return {**r, "estimated_travel_minutes": r.get("eta_minutes"), "origin": {"lat": start_lat, "lng": start_lng}, "destination": {"lat": dest_lat, "lng": dest_lng}}
