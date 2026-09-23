"""External data providers (NADRES, government surveillance, weather) with provenance,
health tracking, timeouts, retries with exponential backoff + jitter, and a circuit breaker.

Honesty rules:
  * A provider without credentials reports CONFIGURATION_REQUIRED and returns no data.
  * A failed live request returns UNAVAILABLE plus the *last successful* snapshot, labelled
    with its original retrieval time and data_status="STALE" — never presented as live.
  * No hardcoded bulletin/census figures are returned as data.
  * The NADRES/DAHD response schemas are not publicly documented. The adapters therefore
    validate only a minimal, explicit contract (documented in docs/INTEGRATIONS.md) and
    reject anything else rather than guessing.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import DataSnapshot, DataSourceStatus, ExternalDataRecord, SurveillanceObservation

logger = logging.getLogger("pashu_shield.external")


async def record_health(provider: str, category: str, ok: bool, error: Optional[str] = None, latency_ms: Optional[float] = None, records: int = 0, configured: bool = True, state: Optional[str] = None) -> None:
    """Persist provider health in its own session so callers' transactions are unaffected."""
    try:
        async with AsyncSessionLocal() as db:
            row = await db.get(DataSourceStatus, provider)
            if row is None:
                row = DataSourceStatus(provider=provider, category=category, records_received=0, consecutive_failures=0)
                db.add(row)
            row.configured = configured
            row.last_latency_ms = latency_ms
            now = datetime.utcnow()
            if ok:
                row.last_success_at = now
                row.consecutive_failures = 0
                row.records_received = (row.records_received or 0) + records
                row.last_error = None
                row.state = state or "LIVE"
            else:
                row.last_failure_at = now
                row.consecutive_failures = (row.consecutive_failures or 0) + 1
                row.last_error = (error or "unknown error")[:500]
                row.state = state or ("UNAVAILABLE" if configured else "CONFIGURATION_REQUIRED")
            await db.commit()
    except Exception:
        logger.exception("could not record provider health", extra={"fields": {"provider": provider}})


class CircuitBreaker:
    def __init__(self, threshold: int = 5, cooldown_s: float = 60.0) -> None:
        self.threshold, self.cooldown_s = threshold, cooldown_s
        self.failures, self.opened_at = 0, 0.0

    def allow(self) -> bool:
        return self.failures < self.threshold or (time.monotonic() - self.opened_at) > self.cooldown_s

    def success(self) -> None:
        self.failures = 0

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()


class ProviderError(Exception):
    pass


class ExternalDataProvider:
    key = "BASE"
    category = "external"
    display_name = "Base"
    required_settings: List[str] = []

    def __init__(self) -> None:
        self.breaker = CircuitBreaker()

    def configured(self) -> bool:
        return all(bool(getattr(settings, s, "")) for s in self.required_settings)

    async def _get_json(self, url: str, *, headers: Optional[dict] = None, params: Optional[dict] = None, attempts: int = 3, timeout: float = 8.0) -> Any:
        """Idempotent GET with timeout, retry (exp backoff + jitter), 429 Retry-After and breaker."""
        if not self.breaker.allow():
            raise ProviderError("circuit open after repeated failures")
        last: Optional[str] = None
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                    resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 429:
                    wait = min(30.0, float(resp.headers.get("retry-after", "2") or 2))
                    last = "rate limited (429)"
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code in (401, 403):
                    self.breaker.failure()
                    raise ProviderError(f"authentication rejected (HTTP {resp.status_code})")
                if resp.status_code >= 500:
                    last = f"HTTP {resp.status_code}"
                elif resp.status_code != 200:
                    self.breaker.failure()
                    raise ProviderError(f"HTTP {resp.status_code}")
                else:
                    self.breaker.success()
                    return resp.json()
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = type(e).__name__
            except ValueError:
                self.breaker.failure()
                raise ProviderError("response is not valid JSON")
            await asyncio.sleep(min(8.0, (2 ** attempt) * 0.5) + random.uniform(0, 0.25))
        self.breaker.failure()
        raise ProviderError(last or "request failed")

    async def last_snapshot(self, record_type: str) -> Optional[ExternalDataRecord]:
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(ExternalDataRecord).where(ExternalDataRecord.provider == self.key, ExternalDataRecord.record_type == record_type).order_by(ExternalDataRecord.retrieved_at.desc()).limit(1))).scalars().first()

    async def store_snapshot(self, record_type: str, payload: Any, request_id: str, source_timestamp: Optional[datetime] = None) -> None:
        async with AsyncSessionLocal() as db:
            db.add(ExternalDataRecord(id=uuid.uuid4().hex, provider=self.key, source=self.display_name, record_type=record_type, payload=payload, data_status="LIVE", request_id=request_id, source_timestamp=source_timestamp, retrieved_at=datetime.utcnow()))
            await db.commit()

    def not_configured(self) -> Dict[str, Any]:
        return {"provider": self.key, "source": self.display_name, "data_status": "CONFIGURATION_REQUIRED", "data": None,
                "required_settings": self.required_settings, "message": f"{self.display_name} is not configured. No data is shown rather than substituting placeholder values."}

    async def unavailable(self, record_type: str, error: str) -> Dict[str, Any]:
        snap = await self.last_snapshot(record_type)
        return {
            "provider": self.key, "source": self.display_name, "data_status": "UNAVAILABLE", "error": error,
            "message": f"{self.display_name}: temporarily unavailable",
            "last_successful_update": snap.retrieved_at.isoformat() if snap else None,
            "stale_data": ({"data_status": "STALE", "retrieved_at": snap.retrieved_at.isoformat(), "data": snap.payload} if snap else None),
            "data": None,
        }


# ---------------------------------------------------------------------------------------
def _validate_observation(item: Any) -> Optional[Dict[str, Any]]:
    """Minimal contract for surveillance feeds. Returns normalised dict or None if invalid."""
    if not isinstance(item, dict):
        return None
    disease = item.get("disease")
    rid = item.get("id") or item.get("record_id")
    observed = item.get("observed_at") or item.get("report_date")
    if not (isinstance(disease, str) and disease and rid and isinstance(observed, str)):
        return None
    try:
        observed_dt = datetime.fromisoformat(observed.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
    if observed_dt > datetime.utcnow():
        return None
    lat, lng = item.get("lat"), item.get("lng")
    if lat is not None and not (isinstance(lat, (int, float)) and -90 <= lat <= 90):
        return None
    if lng is not None and not (isinstance(lng, (int, float)) and -180 <= lng <= 180):
        return None
    try:
        cases = int(item.get("cases", item.get("case_count", 0)) or 0)
        deaths = int(item.get("deaths", item.get("death_count", 0)) or 0)
    except (TypeError, ValueError):
        return None
    if cases < 0 or deaths < 0:
        return None
    return {"source_record_id": str(rid)[:128], "disease": disease[:128], "species": (item.get("species") or None), "district": item.get("district"), "block": item.get("block"),
            "lat": lat, "lng": lng, "case_count": cases, "death_count": deaths, "observed_at": observed_dt,
            "verification_status": "VERIFIED" if item.get("verified") else "OFFICIAL_UNVERIFIED"}


class SurveillanceFeedProvider(ExternalDataProvider):
    """Shared implementation for authorised government surveillance feeds."""
    url_setting = ""
    key_setting = ""
    path = "/observations"

    async def fetch_observations(self, state: str = "Maharashtra") -> Dict[str, Any]:
        if not self.configured():
            await record_health(self.key, self.category, ok=False, error="not configured", configured=False, state="CONFIGURATION_REQUIRED")
            return self.not_configured()
        request_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            data = await self._get_json(getattr(settings, self.url_setting).rstrip("/") + self.path,
                                        headers={"Authorization": f"Bearer {getattr(settings, self.key_setting)}", "Accept": "application/json", "X-Request-ID": request_id},
                                        params={"state": state})
        except ProviderError as e:
            await record_health(self.key, self.category, ok=False, error=str(e), latency_ms=(time.perf_counter() - start) * 1000)
            return await self.unavailable("observations", str(e))
        latency = (time.perf_counter() - start) * 1000
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            await record_health(self.key, self.category, ok=False, error="schema validation failed: expected {items: [...]}", latency_ms=latency, state="DEGRADED")
            return await self.unavailable("observations", "response failed schema validation")
        valid, rejected = [], 0
        for it in items:
            v = _validate_observation(it)
            if v:
                valid.append(v)
            else:
                rejected += 1
        inserted = await self._persist(valid, request_id, data.get("data_version") if isinstance(data, dict) else None, rejected)
        await self.store_snapshot("observations", {"count": len(valid), "rejected": rejected}, request_id)
        await record_health(self.key, self.category, ok=True, latency_ms=latency, records=inserted)
        return {"provider": self.key, "source": self.display_name, "data_status": "LIVE", "request_id": request_id, "retrieved_at": datetime.utcnow().isoformat(),
                "received": len(items), "accepted": len(valid), "rejected": rejected, "inserted": inserted}

    async def _persist(self, rows: List[Dict[str, Any]], request_id: str, data_version: Optional[str], rejected: int) -> int:
        inserted = 0
        async with AsyncSessionLocal() as db:
            for r in rows:
                exists = (await db.execute(select(SurveillanceObservation.id).where(SurveillanceObservation.source_name == self.key, SurveillanceObservation.source_record_id == r["source_record_id"]))).first()
                if exists:
                    continue  # deduplicated on (source_name, source_record_id)
                db.add(SurveillanceObservation(id=uuid.uuid4().hex, source_type="GOVERNMENT", source_name=self.key, request_id=request_id, data_version=data_version, confidence=None, **r))
                inserted += 1
            digest = hashlib.sha256(json.dumps(sorted(r["source_record_id"] for r in rows)).encode()).hexdigest()
            if not (await db.execute(select(DataSnapshot.id).where(DataSnapshot.provider == self.key, DataSnapshot.content_hash == digest))).first():
                db.add(DataSnapshot(id=uuid.uuid4().hex, provider=self.key, dataset="observations", content_hash=digest, record_count=len(rows), quality_report={"accepted": len(rows), "rejected": rejected, "inserted": inserted}))
            await db.commit()
        return inserted


class NADRESProvider(SurveillanceFeedProvider):
    key = "NADRES"
    category = "surveillance"
    display_name = "ICAR-NIVEDI NADRES"
    required_settings = ["NADRES_API_URL", "NADRES_API_KEY"]
    url_setting, key_setting = "NADRES_API_URL", "NADRES_API_KEY"

    async def fetch_disease_forewarning(self, state: str = "Maharashtra") -> Dict[str, Any]:
        """Kept for the existing /external/nadres/bulletin route. Returns the raw forewarning
        payload only when a live, authorised response is obtained."""
        if not self.configured():
            await record_health(self.key, self.category, ok=False, error="not configured", configured=False, state="CONFIGURATION_REQUIRED")
            return self.not_configured()
        request_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            data = await self._get_json(settings.NADRES_API_URL.rstrip("/") + "/forewarning", headers={"Authorization": f"Bearer {settings.NADRES_API_KEY}", "Accept": "application/json"}, params={"state": state})
        except ProviderError as e:
            await record_health(self.key, self.category, ok=False, error=str(e), latency_ms=(time.perf_counter() - start) * 1000)
            return await self.unavailable("forewarning", str(e))
        await self.store_snapshot("forewarning", data, request_id)
        await record_health(self.key, self.category, ok=True, latency_ms=(time.perf_counter() - start) * 1000, records=1)
        return {"provider": self.key, "source": self.display_name, "data_status": "LIVE", "request_id": request_id, "retrieved_at": datetime.utcnow().isoformat(), "data": data,
                "label": "PREDICTED RISK (NADRES forewarning) — not a confirmed outbreak declaration"}


class GovernmentSurveillanceProvider(SurveillanceFeedProvider):
    key = "GOVT_SURVEILLANCE"
    category = "surveillance"
    display_name = "Government surveillance feed (DAHD / State AH Dept.)"
    required_settings = ["GOVERNMENT_API_URL", "GOVERNMENT_API_KEY"]
    url_setting, key_setting = "GOVERNMENT_API_URL", "GOVERNMENT_API_KEY"


class LivestockCensusProvider(ExternalDataProvider):
    """20th Livestock Census reference data. There is no public census API; figures must be
    imported from the official DAHD publication via the ingestion endpoint. Until imported,
    no numbers are shown."""
    key = "DAHD_CENSUS"
    category = "reference"
    display_name = "DAHD 20th Livestock Census (historical reference)"

    def configured(self) -> bool:
        return True

    async def get_district_census(self, district: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            snap = (await db.execute(select(ExternalDataRecord).where(ExternalDataRecord.provider == self.key, ExternalDataRecord.external_id == district.lower()).order_by(ExternalDataRecord.retrieved_at.desc()).limit(1))).scalars().first()
        if not snap:
            return {"provider": self.key, "source": self.display_name, "data_status": "NOT_IMPORTED", "district": district, "data": None,
                    "message": "Census figures have not been imported. Import the official DAHD dataset via POST /api/v1/external/ingest/census."}
        return {"provider": self.key, "source": self.display_name, "data_status": "HISTORICAL", "district": district, "data": snap.payload,
                "reference_year": (snap.payload or {}).get("reference_year"), "imported_at": snap.retrieved_at.isoformat()}


class WeatherProvider(ExternalDataProvider):
    key = "WEATHER_OPEN_METEO"
    category = "weather"
    display_name = "Open-Meteo"

    def configured(self) -> bool:
        return settings.WEATHER_PROVIDER == "open_meteo" and bool(settings.WEATHER_API_URL)

    async def get_district_weather(self, lat: float, lng: float) -> Dict[str, Any]:
        if not self.configured():
            return self.not_configured()
        start = time.perf_counter()
        try:
            data = await self._get_json(settings.WEATHER_API_URL.rstrip("/") + "/forecast",
                                        params={"latitude": lat, "longitude": lng, "current": "temperature_2m,relative_humidity_2m,precipitation"}, attempts=2, timeout=5.0)
            current = data.get("current") if isinstance(data, dict) else None
            if not isinstance(current, dict) or "temperature_2m" not in current:
                raise ProviderError("schema validation failed")
        except ProviderError as e:
            await record_health(self.key, self.category, ok=False, error=str(e), latency_ms=(time.perf_counter() - start) * 1000)
            return await self.unavailable("current", str(e))
        await record_health(self.key, self.category, ok=True, latency_ms=(time.perf_counter() - start) * 1000, records=1)
        result = {"source": self.display_name, "provider": self.key, "data_status": "LIVE",
                  "temperature_c": current.get("temperature_2m"), "humidity_percent": current.get("relative_humidity_2m"),
                  "precipitation_mm": current.get("precipitation"), "observed_at": current.get("time"), "retrieved_at": datetime.utcnow().isoformat(),
                  "lat": lat, "lng": lng}
        await self.store_snapshot("current", result, uuid.uuid4().hex)
        return result


nadres_provider = NADRESProvider()
government_provider = GovernmentSurveillanceProvider()
census_provider = LivestockCensusProvider()
weather_provider = WeatherProvider()
