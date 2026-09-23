"""Background worker: `python -m backend.worker`.

Executes queued jobs (notifications, dispatch expiry, reminders, outbreak detection, ingestion,
retention cleanup) and enqueues scheduled jobs. Safe to run several replicas on PostgreSQL
(SKIP LOCKED); the scheduler uses dedup keys so duplicate schedules collapse.
"""
import asyncio
import logging
import signal

from backend.middleware import configure_logging
from backend.services.jobs import worker_loop

logger = logging.getLogger("pashu_shield.worker")


async def main() -> None:
    configure_logging()
    from backend.init_db import init_schema
    await init_schema()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover
            pass
    logger.info("worker started")
    await worker_loop(stop)
    logger.info("worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
