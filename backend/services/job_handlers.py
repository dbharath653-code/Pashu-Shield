"""Registered background job handlers (imported by jobs.worker_loop)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Animal, IdempotencyRecord, OutbreakEvent, StoredFile, User, VaccinationRecord
from backend.services.jobs import handler


@handler("notification.deliver")
async def deliver_notification(db: AsyncSession, payload: Dict[str, Any]):
    from backend.services.notification_service import NotificationService
    return await NotificationService.deliver(db, payload["notification_id"])


@handler("dispatch.expire_offers")
async def expire_offers(db: AsyncSession, payload: Dict[str, Any]):
    from backend.services.dispatch_service import DispatchEngine
    return {"expired": await DispatchEngine.expire_stale_requests(db)}


@handler("vaccination.reminders")
async def vaccination_reminders(db: AsyncSession, payload: Dict[str, Any]):
    """Queue reminders for doses due within 3 days (once per record, consent-checked)."""
    from backend.services.notification_service import NotificationService
    now = datetime.utcnow()
    due = (await db.execute(select(VaccinationRecord).where(VaccinationRecord.next_due_date.isnot(None), VaccinationRecord.next_due_date <= now + timedelta(days=3),
                                                            VaccinationRecord.next_due_date >= now - timedelta(days=1), VaccinationRecord.reminder_sent_at.is_(None)).limit(500))).scalars().all()
    queued = 0
    for rec in due:
        animal = await db.get(Animal, rec.animal_id)
        owner = await db.get(User, animal.owner_id) if animal else None
        if owner:
            await NotificationService.queue(db, channel="SMS", template="VACCINATION_DUE", context={"disease": rec.disease, "due_date": rec.next_due_date.strftime("%d %b %Y"), "animal_id": animal.tag_id},
                                            user=owner, dedup_key=f"vacc-due:{rec.id}")
            queued += 1
        rec.reminder_sent_at = now
    await db.commit()
    return {"reminders": queued}


@handler("outbreak.detect")
async def outbreak_detect(db: AsyncSession, payload: Dict[str, Any]):
    """Detect clusters and raise evidence-labelled alerts. Only clusters at or above
    VETERINARIAN_VERIFIED create an OutbreakEvent; REPORTED clusters create a
    'possible cluster — unverified' alert only."""
    from backend.services.alert_engine import raise_alert
    from backend.services.events import Event
    from backend.services.outbreak_service import detect_clusters
    result = await detect_clusters(db)
    created = 0
    for c in result["clusters"]:
        day = datetime.utcnow().strftime("%Y%m%d")
        verified = c["evidence_level"] in ("VETERINARIAN_VERIFIED", "LAB_CONFIRMED")
        alert, is_new = await raise_alert(
            db, alert_type="OUTBREAK_CLUSTER", severity="CRITICAL" if c["evidence_level"] == "LAB_CONFIRMED" else ("HIGH" if verified else "MEDIUM"),
            title=f"{'Verified' if verified else 'Possible (unverified)'} {c['disease']} cluster – {c['district']}",
            message=f"{c['record_count']} records / {c['cases']} animals within {c['radius_km']} km. Evidence: {c['evidence_level']}.",
            dedup_key=f"cluster:{c['district']}:{c['disease']}:{c['evidence_level']}:{day}", district=c["district"], disease=c["disease"],
            target_roles=["VETERINARIAN", "DISTRICT_OFFICER", "BLOCK_OFFICER", "STATE_OFFICER"], evidence_level=c["evidence_level"], is_demo=c.get("is_demo", False))
        if verified:
            exists = (await db.execute(select(OutbreakEvent.id).where(OutbreakEvent.district == c["district"], OutbreakEvent.disease == c["disease"], OutbreakEvent.status == "Active"))).first()
            if not exists:
                db.add(OutbreakEvent(id=uuid.uuid4().hex, outbreak_code=f"OB-{c['district'][:3].upper()}-{day}-{uuid.uuid4().hex[:4].upper()}", disease=c["disease"], district=c["district"],
                                     center_lat=c["lat"], center_lng=c["lng"], radius_km=c["radius_km"], affected_count=c["cases"], death_count=c.get("deaths", 0),
                                     evidence_level=c["evidence_level"], evidence={"record_ids": c.get("contributing_records", [])}, detection_method="DENSITY_CLUSTER",
                                     severity="High", is_demo=c.get("is_demo", False)))
                created += 1
        if is_new:
            await db.commit()
            await Event("outbreak.detected", {"district": c["district"], "disease": c["disease"], "evidence": c["evidence_level"], "alertId": alert.id}, district=c["district"]).publish()
    await db.commit()
    return {"clusters": len(result["clusters"]), "outbreak_events_created": created}


@handler("ingest.nadres")
async def ingest_nadres(db: AsyncSession, payload: Dict[str, Any]):
    from backend.services.external_data_service import nadres_provider
    res = await nadres_provider.fetch_observations()
    return {k: res.get(k) for k in ("data_status", "accepted", "rejected", "inserted", "error")}


@handler("ingest.government")
async def ingest_government(db: AsyncSession, payload: Dict[str, Any]):
    from backend.services.external_data_service import government_provider
    res = await government_provider.fetch_observations()
    return {k: res.get(k) for k in ("data_status", "accepted", "rejected", "inserted", "error")}


@handler("cleanup.retention")
async def cleanup_retention(db: AsyncSession, payload: Dict[str, Any]):
    from backend.services.file_service import resolve_path
    now = datetime.utcnow()
    files = (await db.execute(select(StoredFile).where(StoredFile.expires_at.isnot(None), StoredFile.expires_at < now, StoredFile.deleted_at.is_(None)).limit(1000))).scalars().all()
    for f in files:
        try:
            resolve_path(f.storage_key).unlink(missing_ok=True)
        except Exception:
            pass
        f.deleted_at = now
    old_idem = (await db.execute(select(IdempotencyRecord).where(IdempotencyRecord.created_at < now - timedelta(days=30)).limit(5000))).scalars().all()
    for r in old_idem:
        await db.delete(r)
    await db.commit()
    return {"files_deleted": len(files), "idempotency_pruned": len(old_idem)}


@handler("health.providers")
async def provider_health(db: AsyncSession, payload: Dict[str, Any]):
    """Only probes providers that are configured; never marks anything LIVE without a real response."""
    from backend.services.external_data_service import weather_provider
    if weather_provider.configured():
        r = await weather_provider.get_district_weather(18.5204, 73.8567)
        return {"weather": r.get("data_status"), "environment": settings.ENVIRONMENT}
    return {"weather": "CONFIGURATION_REQUIRED"}


@handler("call.process_recording")
async def process_call_recording(db: AsyncSession, payload: Dict[str, Any]):
    """Audio -> speech-to-text -> structured extraction -> AI/template summary.

    Honesty rules:
      * STT not configured => transcription_status stays NOT_CONFIGURED (no invented transcript),
      * extraction only fills fields actually present in the transcript (rest stay None),
      * the summary never claims a diagnosis.
    """
    import uuid as _uuid
    from backend.models import CallSession, CallTranscript
    from backend.services.call_events import publish_call_event
    from backend.services.voice import extract_fields, generate_summary, transcribe_audio

    session = await db.get(CallSession, payload.get("call_session_id"))
    if session is None or not session.recording_url:
        return {"skipped": True}
    if session.transcription_status == "COMPLETED":
        return {"skipped": True, "reason": "already processed"}

    from backend.services.telephony import get_provider

    provider = get_provider()
    try:
        audio, content_type = await provider.download_recording(session.recording_url)
    except Exception as e:
        session.transcription_status = "FAILED"
        session.last_error = f"recording_download:{type(e).__name__}"
        await db.commit()
        return {"status": "FAILED", "stage": "download"}

    stt = await transcribe_audio(audio, filename=f"{session.id}.{'wav' if 'wav' in (content_type or '') else 'mp3'}",
                                 content_type=content_type)
    if stt["status"] == "NOT_CONFIGURED":
        session.transcription_status = "NOT_CONFIGURED"
        await db.commit()
        # Still build a summary? No — without a transcript there is nothing to summarise
        # beyond "recording available; transcription not configured".
        return {"status": "NOT_CONFIGURED"}
    if stt["status"] != "COMPLETED" or not stt.get("text"):
        session.transcription_status = "FAILED"
        await db.commit()
        return {"status": "FAILED", "stage": "stt"}

    text = stt["text"]
    db.add(CallTranscript(
        id=f"TRN-{_uuid.uuid4().hex[:10].upper()}", call_session_id=session.id,
        speaker="MIXED",  # single-pass STT cannot attribute speakers honestly
        text=text, start_time=0.0, confidence=None,
        language=stt.get("language") or session.language, source="STT",
    ))
    fields = extract_fields(text)
    summary = await generate_summary(fields, transcript=text)
    session.ai_summary = summary["summary"]
    session.transcription_status = "COMPLETED"
    await db.commit()
    await publish_call_event("call.transcript_updated", session, {"callSessionId": session.id})
    await publish_call_event("call.summary_updated", session, {"provider": summary["provider"]})
    return {"status": "COMPLETED", "summary_provider": summary["provider"]}



@handler("call.cleanup_recordings")
async def cleanup_call_recordings(db: AsyncSession, payload: Dict[str, Any]):
    """Retention: clear private recording references older than VOICE_RECORDING_RETENTION_DAYS
    (metadata, transcripts and summaries are retained; the URL can no longer be fetched)."""
    from datetime import datetime, timedelta
    from backend.models import CallSession
    cutoff = datetime.utcnow() - timedelta(days=settings.VOICE_RECORDING_RETENTION_DAYS)
    rows = (await db.execute(
        select(CallSession).where(CallSession.recording_url.isnot(None),
                                  CallSession.ended_at.isnot(None),
                                  CallSession.ended_at < cutoff).limit(500))).scalars().all()
    for s in rows:
        s.recording_url = None
        s.recording_sid = None
        s.recording_status = "EXPIRED"
    await db.commit()
    return {"recordings_expired": len(rows)}
