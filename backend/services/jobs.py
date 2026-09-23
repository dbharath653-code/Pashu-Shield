"""Durable job queue backed by the primary database (table `jobs`).

Why DB-backed: the stack already runs PostgreSQL; a transactional outbox-style queue means a
job is enqueued atomically with the business write that caused it (no lost notifications when
Redis is down) and needs no extra broker. Workers claim jobs with
`SELECT ... FOR UPDATE SKIP LOCKED` on PostgreSQL, so several workers can run safely.

States: QUEUED -> RUNNING -> COMPLETED | RETRYING (exp. backoff) -> ... -> DEAD_LETTER.

JOB_BACKEND:
  worker -> a separate `python -m backend.worker` process executes jobs (production).
  inline -> the API process runs a background poller (development / single-node).
"""
from __future__ import annotations

import asyncio
import logging
import random
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Job

logger = logging.getLogger("pashu_shield.jobs")


class RetryableError(Exception):
    """Transient failure: the job will be retried with backoff."""


class PermanentError(Exception):
    """Non-retryable failure: the job goes straight to DEAD_LETTER."""


Handler = Callable[[AsyncSession, Dict[str, Any]], Awaitable[Any]]
HANDLERS: Dict[str, Handler] = {}


def handler(job_type: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[job_type] = fn
        return fn
    return deco


async def enqueue(db: AsyncSession, job_type: str, payload: Dict[str, Any], *, dedup_key: Optional[str] = None,
                  run_after: Optional[datetime] = None, max_attempts: int = 5) -> Job:
    """Add a job in the caller's transaction (caller commits)."""
    if dedup_key:
        existing = (await db.execute(select(Job).where(Job.dedup_key == dedup_key, Job.status.in_(["QUEUED", "RUNNING", "RETRYING"])))).scalars().first()
        if existing:
            return existing
    job = Job(id=f"JOB-{uuid.uuid4().hex[:12].upper()}", job_type=job_type, payload=payload, dedup_key=dedup_key,
              run_after=run_after or datetime.utcnow(), max_attempts=max_attempts, status="QUEUED")
    db.add(job)
    await db.flush()
    return job


def _backoff(attempt: int) -> timedelta:
    return timedelta(seconds=min(3600, (2 ** attempt) * 5) + random.uniform(0, 3))


async def _claim(db: AsyncSession, limit: int) -> List[Job]:
    now = datetime.utcnow()
    stmt = (select(Job).where(Job.status.in_(["QUEUED", "RETRYING"]), or_(Job.run_after.is_(None), Job.run_after <= now))
            .order_by(Job.run_after).limit(limit))
    if settings.is_postgres:
        stmt = stmt.with_for_update(skip_locked=True)
    jobs = (await db.execute(stmt)).scalars().all()
    for j in jobs:
        j.status, j.started_at = "RUNNING", now
        j.attempts += 1
    await db.commit()
    return list(jobs)


async def run_job(job_id: str) -> str:
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if job is None:
            return "MISSING"
        fn = HANDLERS.get(job.job_type)
        try:
            if fn is None:
                raise PermanentError(f"No handler registered for {job.job_type}")
            result = await fn(db, job.payload or {})
            job = await db.get(Job, job_id)
            job.status, job.result, job.error, job.finished_at = "COMPLETED", (result if isinstance(result, (dict, list)) else {"result": result}), None, datetime.utcnow()
        except PermanentError as e:
            await db.rollback()
            job = await db.get(Job, job_id)
            job.status, job.error, job.finished_at = "DEAD_LETTER", str(e)[:2000], datetime.utcnow()
        except Exception as e:  # RetryableError or unexpected
            await db.rollback()
            job = await db.get(Job, job_id)
            job.error = (str(e) or type(e).__name__)[:1000] + ("" if isinstance(e, RetryableError) else "\n" + traceback.format_exc(limit=3)[-900:])
            if job.attempts >= job.max_attempts:
                job.status, job.finished_at = "DEAD_LETTER", datetime.utcnow()
            else:
                job.status, job.run_after = "RETRYING", datetime.utcnow() + _backoff(job.attempts)
            logger.warning("job failed", extra={"fields": {"job_id": job_id, "job_type": job.job_type, "attempt": job.attempts, "status": job.status}})
        await db.commit()
        return job.status


async def run_pending(limit: int = 20) -> int:
    async with AsyncSessionLocal() as db:
        jobs = await _claim(db, limit)
    for j in jobs:
        await run_job(j.id)
    return len(jobs)


async def recover_stuck(older_than_minutes: int = 15) -> int:
    """Jobs left RUNNING by a crashed worker are returned to the queue."""
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        stuck = (await db.execute(select(Job).where(Job.status == "RUNNING", Job.started_at < cutoff))).scalars().all()
        for j in stuck:
            j.status, j.run_after, j.error = "RETRYING", datetime.utcnow(), "recovered after worker interruption"
        await db.commit()
        return len(stuck)


# ---- scheduled jobs (cron-like) -----------------------------------------------------------
SCHEDULE: List[tuple[str, int]] = [
    ("dispatch.expire_offers", 60),
    ("vaccination.reminders", 3600),
    ("outbreak.detect", 900),
    ("ingest.nadres", 6 * 3600),
    ("ingest.government", 6 * 3600),
    ("cleanup.retention", 24 * 3600),
    ("call.cleanup_recordings", 24 * 3600),
    ("health.providers", 300),
]
_last_scheduled: Dict[str, datetime] = {}


async def schedule_due() -> None:
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        for job_type, every in SCHEDULE:
            last = _last_scheduled.get(job_type)
            if last is None or (now - last).total_seconds() >= every:
                bucket = int(now.timestamp() // every)
                await enqueue(db, job_type, {}, dedup_key=f"sched:{job_type}:{bucket}", max_attempts=3)
                _last_scheduled[job_type] = now
        await db.commit()


async def worker_loop(stop: asyncio.Event, poll_seconds: float = 2.0, with_scheduler: bool = True) -> None:
    import backend.services.job_handlers  # noqa: F401  (registers handlers)
    await recover_stuck()
    while not stop.is_set():
        try:
            if with_scheduler:
                await schedule_due()
            n = await run_pending()
        except Exception:
            logger.exception("worker iteration failed")
            n = 0
        if n == 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
            except asyncio.TimeoutError:
                pass
