"""Road routing / ETA providers.

A road ETA is only returned when a real routing engine answers. Without one, the response is
`ETA_UNAVAILABLE` with the straight-line distance explicitly labelled as such — never a
fabricated travel time.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from backend.config import settings
from backend.services.spatial import haversine_distance


class RoutingProvider:
    name = "none"

    def configured(self) -> bool:
        return False

    async def route(self, o_lat: float, o_lng: float, d_lat: float, d_lng: float) -> Dict[str, Any]:
        return unavailable(o_lat, o_lng, d_lat, d_lng, "No routing provider configured (set ROUTING_PROVIDER=osrm and OSRM_URL)")


def unavailable(o_lat, o_lng, d_lat, d_lng, reason: str) -> Dict[str, Any]:
    return {
        "eta_status": "ETA_UNAVAILABLE",
        "eta_minutes": None,
        "road_distance_km": None,
        "straight_line_distance_km": round(haversine_distance(o_lat, o_lng, d_lat, d_lng), 2),
        "distance_basis": "STRAIGHT_LINE",
        "geometry": None,
        "provider": None,
        "reason": reason,
    }


class OSRMProvider(RoutingProvider):
    """OSRM HTTP API (self-hosted recommended; the public demo server is not for production)."""
    name = "osrm"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def configured(self) -> bool:
        return bool(self.base_url)

    async def route(self, o_lat, o_lng, d_lat, d_lng) -> Dict[str, Any]:
        from backend.services.external_data_service import record_health
        url = f"{self.base_url}/route/v1/driving/{o_lng},{o_lat};{d_lng},{d_lat}"
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, params={"overview": "simplified", "geometries": "geojson"})
            latency = (time.perf_counter() - start) * 1000
            data = resp.json() if resp.status_code == 200 else {}
            routes = data.get("routes") or []
            if data.get("code") != "Ok" or not routes:
                await record_health("ROUTING_OSRM", "routing", ok=False, error=f"HTTP {resp.status_code} code={data.get('code')}", latency_ms=latency)
                return unavailable(o_lat, o_lng, d_lat, d_lng, "Routing engine returned no route")
            r = routes[0]
            await record_health("ROUTING_OSRM", "routing", ok=True, latency_ms=latency, records=1)
            return {
                "eta_status": "ROAD_ETA",
                "eta_minutes": round(float(r["duration"]) / 60.0, 1),
                "road_distance_km": round(float(r["distance"]) / 1000.0, 2),
                "straight_line_distance_km": round(haversine_distance(o_lat, o_lng, d_lat, d_lng), 2),
                "distance_basis": "ROAD",
                "geometry": r.get("geometry"),
                "provider": "osrm",
                "reason": None,
            }
        except (httpx.HTTPError, ValueError, KeyError) as e:
            await record_health("ROUTING_OSRM", "routing", ok=False, error=type(e).__name__)
            return unavailable(o_lat, o_lng, d_lat, d_lng, "Routing engine unreachable")


def get_routing_provider() -> RoutingProvider:
    if settings.ROUTING_PROVIDER == "osrm" and settings.OSRM_URL:
        return OSRMProvider(settings.OSRM_URL)
    return RoutingProvider()


async def route(o_lat: Optional[float], o_lng: Optional[float], d_lat: Optional[float], d_lng: Optional[float]) -> Dict[str, Any]:
    if None in (o_lat, o_lng, d_lat, d_lng):
        return {"eta_status": "ETA_UNAVAILABLE", "eta_minutes": None, "distance_basis": "LOCATION_UNAVAILABLE", "straight_line_distance_km": None, "road_distance_km": None, "geometry": None, "provider": None, "reason": "Origin or destination location unavailable"}
    return await get_routing_provider().route(o_lat, o_lng, d_lat, d_lng)
