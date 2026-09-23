"""Spatial query layer.

On PostgreSQL+PostGIS (migration 0002) queries run in the database using the generated
`geog geography(Point,4326)` columns and GiST indexes (ST_DWithin / ST_Distance).
On SQLite (local development/tests only) the same functions fall back to a bounding-box
pre-filter in SQL plus exact haversine in Python. Results report which engine was used.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings

EARTH_RADIUS_KM = 6371.0088


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def valid_coordinates(lat: Optional[float], lng: Optional[float]) -> bool:
    return lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0)


def bbox_for_radius(lat: float, lng: float, radius_km: float) -> Tuple[float, float, float, float]:
    dlat = radius_km / 111.32
    dlng = radius_km / (111.32 * max(0.01, math.cos(math.radians(lat))))
    return lat - dlat, lng - dlng, lat + dlat, lng + dlng


def parse_bbox(bbox: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """bbox = "minLng,minLat,maxLng,maxLat" (GeoJSON order)."""
    if not bbox:
        return None
    try:
        min_lng, min_lat, max_lng, max_lat = (float(x) for x in bbox.split(","))
    except ValueError:
        raise ValueError("bbox must be minLng,minLat,maxLng,maxLat")
    if not (-180 <= min_lng < max_lng <= 180 and -90 <= min_lat < max_lat <= 90):
        raise ValueError("bbox out of range")
    return min_lat, min_lng, max_lat, max_lng


_postgis_available: Optional[bool] = None


async def postgis_enabled(db: AsyncSession) -> bool:
    global _postgis_available
    if not settings.is_postgres:
        return False
    if _postgis_available is None:
        try:
            await db.execute(text("SELECT postgis_version()"))
            _postgis_available = True
        except Exception:
            _postgis_available = False
    return _postgis_available


async def vets_within(db: AsyncSession, lat: float, lng: float, radius_km: float) -> Tuple[List[Dict[str, Any]], str]:
    """Veterinarians with a known current location within radius, nearest first."""
    if await postgis_enabled(db):
        rows = (await db.execute(text(
            """
            SELECT p.user_id, ST_Distance(p.geog, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography)/1000.0 AS km
            FROM veterinarian_profiles p
            WHERE p.geog IS NOT NULL
              AND ST_DWithin(p.geog, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography, :m)
            ORDER BY km
            """), {"lat": lat, "lng": lng, "m": radius_km * 1000.0})).all()
        return [{"user_id": r[0], "distance_km": round(float(r[1]), 2)} for r in rows], "POSTGIS"

    min_lat, min_lng, max_lat, max_lng = bbox_for_radius(lat, lng, radius_km)
    rows = (await db.execute(text(
        """
        SELECT user_id, current_lat, current_lng FROM veterinarian_profiles
        WHERE current_lat BETWEEN :a AND :c AND current_lng BETWEEN :b AND :d
        """), {"a": min_lat, "b": min_lng, "c": max_lat, "d": max_lng})).all()
    out = []
    for uid, vlat, vlng in rows:
        d = haversine_distance(lat, lng, vlat, vlng)
        if d <= radius_km:
            out.append({"user_id": uid, "distance_km": round(d, 2)})
    out.sort(key=lambda x: x["distance_km"])
    return out, "PYTHON_HAVERSINE_DEV"


async def points_in_bbox(db: AsyncSession, table: str, lat_col: str, lng_col: str, bbox: Tuple[float, float, float, float], where: str = "1=1", params: Optional[dict] = None, limit: int = 2000) -> List[Any]:
    """Generic bbox fetch used by GIS layers. `table`/columns are internal constants, never user input."""
    min_lat, min_lng, max_lat, max_lng = bbox
    q = text(f"SELECT * FROM {table} WHERE {lat_col} BETWEEN :a AND :c AND {lng_col} BETWEEN :b AND :d AND {where} LIMIT :lim")
    return (await db.execute(q, {"a": min_lat, "b": min_lng, "c": max_lat, "d": max_lng, "lim": limit, **(params or {})})).mappings().all()
