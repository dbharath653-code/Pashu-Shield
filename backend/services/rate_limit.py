"""Fixed-window rate limiting. Redis-backed when RATE_LIMIT_BACKEND=redis (required in
production, shared across workers); in-memory otherwise (single-process dev/test)."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request

from backend.config import settings


class _MemoryStore:
    def __init__(self) -> None:
        self.buckets: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    async def hit(self, key: str, window: int) -> int:
        count, reset = self.buckets[key]
        now = time.time()
        if now >= reset:
            count, reset = 0, now + window
        count += 1
        self.buckets[key] = (count, reset)
        return count

    def reset(self) -> None:
        self.buckets.clear()


class _RedisStore:
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis  # imported lazily; only needed when configured
        self.client = redis.from_url(url)

    async def hit(self, key: str, window: int) -> int:
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        count, _ = await pipe.execute()
        return int(count)

    def reset(self) -> None:  # pragma: no cover
        pass


_store = _RedisStore(settings.REDIS_URL) if settings.RATE_LIMIT_BACKEND == "redis" and settings.REDIS_URL else _MemoryStore()

# name -> (max requests, window seconds)
LIMITS: Dict[str, Tuple[int, int]] = {
    "login": (10, 60),
    "signup": (5, 300),
    "refresh": (30, 60),
    "report": (30, 60),
    "voice": (20, 60),
    "upload": (20, 300),
    "external": (30, 60),
    "sync": (60, 60),
    "notify": (20, 60),
    # Per IVR *call* (keyed on the provider call id, not the source IP: every Exotel
    # webhook arrives from Exotel's own egress range). A real IVR call produces a couple of
    # dozen webhooks; this bounds a stuck or abusive flow.
    "ivr_call": (60, 300),
}


def client_ip(request: Request) -> str:
    # X-Forwarded-For is only meaningful behind a trusted proxy; take the left-most hop.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


async def enforce(name: str, identity: str) -> None:
    limit, window = LIMITS[name]
    count = await _store.hit(f"rl:{name}:{identity}", window)
    if count > limit:
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": f"Too many requests. Try again in up to {window} seconds."}, headers={"Retry-After": str(window)})


def limiter(name: str):
    async def dep(request: Request) -> None:
        await enforce(name, client_ip(request))
    return dep


def reset_all() -> None:
    _store.reset()
