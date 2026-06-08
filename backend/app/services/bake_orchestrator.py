"""BakeJob lifecycle — engine-agnostic. Shared by the buffer bake and entry rebake.

Imports no bake engine and no API module, so it can be imported by both `buffer.py`
and `entries.py` without circular dependencies. The caller passes an `engine`
coroutine factory `(report) -> Awaitable[list[Entry]]`.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from bson import ObjectId
from beanie.operators import Set

from app.models.bake_job import BakeJob, BakeJobStatus
from app.core.events import event_bus
from app.core.config import settings
from app.services.blocks import blocks_to_text

logger = logging.getLogger(__name__)

Engine = Callable[[Callable], Awaitable[list]]
"""async (report) -> list[Entry]; `report(completed, total, label, phase)`."""


def serialize_bake_job(job: BakeJob) -> dict:
    return {
        "id": str(job.id),
        "status": job.status.value,
        "total_steps": job.total_steps,
        "completed_steps": job.completed_steps,
        "current_label": job.current_label,
        "phase": job.phase,
        "started_at": job.created_at.isoformat(),
    }


async def active_bake(uid: ObjectId) -> Optional[BakeJob]:
    """Return the user's current running bake, or None.

    A running job whose heartbeat is older than `bake_stale_seconds` is treated
    as orphaned: it is marked FAILED and None is returned, so a new bake can start.
    """
    job = await BakeJob.find_one(
        {"user_id": uid, "status": BakeJobStatus.RUNNING}
    )
    if job is None:
        return None

    cutoff = datetime.utcnow() - timedelta(seconds=settings.bake_stale_seconds)
    if job.heartbeat_at < cutoff:
        job.status = BakeJobStatus.FAILED
        job.error_message = "stale: no heartbeat"
        job.updated_at = datetime.utcnow()
        await job.save()
        return None

    return job


async def fail_orphaned_bakes() -> int:
    """Mark every still-running bake job FAILED. Called on app startup so a
    restart mid-bake never leaves a permanent lock. Returns the count recovered."""
    jobs = await BakeJob.find(
        {"status": BakeJobStatus.RUNNING}
    ).to_list()
    for job in jobs:
        job.status = BakeJobStatus.FAILED
        job.error_message = "interrupted by restart"
        job.updated_at = datetime.utcnow()
        await job.save()
    return len(jobs)


async def launch_bake(uid: ObjectId, user_id: str, total_steps: int, engine: "Engine") -> BakeJob:
    """Insert a BakeJob, kick off `run_bake_job(engine)`, publish bake:started, return the job.

    Lets `pymongo.errors.DuplicateKeyError` propagate (the partial-unique-index race
    backstop -> the caller maps it to 409). Callers must perform their own pre-checks
    (active bake, empty input) before calling.
    """
    job = BakeJob(user_id=uid, total_steps=total_steps)
    await job.insert()
    asyncio.create_task(run_bake_job(str(job.id), user_id, uid, engine))
    await event_bus.publish(user_id, "bake:started", serialize_bake_job(job))
    return job


async def run_bake_job(job_id: str, user_id: str, uid: ObjectId, engine: "Engine"):
    """Own a BakeJob: heartbeat ticker, progress reports, guarded terminal writes, SSE.

    `engine(report)` returns the list of affected entries. A heartbeat ticker refreshes
    ``heartbeat_at`` on a fixed interval for the whole run, so a long-but-healthy bake
    (e.g. a slow highlights phase that makes many sequential Claude calls) is never
    mistaken for a dead one by ``active_bake``'s stale-timeout. All terminal writes are
    guarded on the job still being RUNNING, so a job that was already recovered (stale or
    restart) is never silently resurrected.
    """
    oid = ObjectId(job_id)
    job = await BakeJob.get(oid)
    if job is None:
        logger.error("Bake job %s vanished before run", job_id)
        return

    async def report(completed: int, total: int, label: str, phase: str):
        await BakeJob.find_one({"_id": oid, "status": BakeJobStatus.RUNNING}).update(
            Set({
                "completed_steps": completed,
                "total_steps": total,
                "current_label": label,
                "phase": phase,
                "heartbeat_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        )
        await event_bus.publish(user_id, "bake:progress", {
            "completed": completed, "total": total, "label": label, "phase": phase,
        })

    heartbeat_interval = max(10, settings.bake_stale_seconds // 5)

    async def heartbeat_ticker():
        """Keep heartbeat_at fresh while the bake runs, independent of phase length."""
        try:
            while True:
                await asyncio.sleep(heartbeat_interval)
                await BakeJob.find_one({"_id": oid, "status": BakeJobStatus.RUNNING}).update(
                    Set({"heartbeat_at": datetime.utcnow()})
                )
        except asyncio.CancelledError:
            pass

    ticker = asyncio.create_task(heartbeat_ticker())
    try:
        logger.info("Bake job %s started for user %s", job_id, user_id)
        entries = await engine(report)
        logger.info("Bake job %s completed for user %s: %d entries", job_id, user_id, len(entries))

        result_entries = [
            {"id": str(e.id), "date": e.date.isoformat(), "preview": blocks_to_text(e.blocks)[:200]}
            for e in entries
        ]

        fresh = await BakeJob.get(oid)
        if fresh is None or fresh.status != BakeJobStatus.RUNNING:
            logger.warning(
                "Bake job %s no longer RUNNING at completion (status=%s); skipping completion write",
                job_id, getattr(fresh, "status", None),
            )
            return

        fresh.status = BakeJobStatus.COMPLETED
        fresh.completed_steps = fresh.total_steps
        fresh.entries_created = len(entries)
        fresh.result_entries = result_entries
        fresh.phase = None
        fresh.current_label = None
        fresh.heartbeat_at = datetime.utcnow()
        fresh.updated_at = datetime.utcnow()
        await fresh.save()

        await event_bus.publish(user_id, "bake:complete", {
            "entries_created": len(entries),
            "entries": result_entries,
        })
    except Exception as exc:
        logger.exception("Bake job %s failed for user %s: %s", job_id, user_id, exc)
        fresh = await BakeJob.get(oid)
        if fresh is not None and fresh.status == BakeJobStatus.RUNNING:
            fresh.status = BakeJobStatus.FAILED
            fresh.error_message = str(exc)[:300]
            fresh.updated_at = datetime.utcnow()
            await fresh.save()
        try:
            await event_bus.publish(user_id, "bake:error", {"detail": str(exc)[:300]})
        except Exception:
            logger.exception("Failed to publish bake:error event")
    finally:
        ticker.cancel()
        await asyncio.gather(ticker, return_exceptions=True)
