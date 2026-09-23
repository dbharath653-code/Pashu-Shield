"""Single implementation of the disease-report pipeline used by every entry point
(REST, offline sync, voice assistant, IVR):

    validate -> rule triage -> persist report (SUBMITTED -> TRIAGED) -> case + dispatch offer
    -> deduplicated alert -> queued notifications -> surveillance event -> audit
All steps run in one DB transaction; WebSocket events are emitted after commit.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import DiseaseReport, User, UserRole, VeterinaryCase
from backend.schemas import DiseaseReportCreate
from backend.services.alert_engine import raise_alert
from backend.services.audit_service import AuditService
from backend.services.dispatch_service import DispatchEngine
from backend.services.events import Event
from backend.services.notification_service import NotificationService
from backend.services.triage_service import TemperatureError, TriageEngine
from backend.services.workflow import record_transition, transition

SOURCE_TYPES = {
    UserRole.FARMER.value: "FARMER_REPORT",
    UserRole.VETERINARIAN.value: "VETERINARY_REPORT",
    UserRole.PARA_VET.value: "VETERINARY_REPORT",
}


def serialize_report(r: DiseaseReport) -> Dict[str, Any]:
    return {
        "id": r.id, "reportNumber": r.report_number, "date": r.created_at.strftime("%Y-%m-%d") if r.created_at else None,
        "createdAt": r.created_at.isoformat() if r.created_at else None, "species": r.species,
        "numberAffected": r.number_affected, "numberDead": r.number_dead, "district": r.district, "taluka": r.taluka,
        "village": r.village, "lat": r.lat, "lng": r.lng, "locationStatus": r.location_status, "symptoms": r.symptoms or [],
        "temperatureC": r.temperature_c, "status": r.status, "disease": r.suspected_disease,
        "triageRiskLevel": r.triage_risk_level, "triageUrgency": r.triage_urgency, "triageRecommendations": r.triage_recommendations,
        "triageConfidence": r.triage_confidence, "triageRuleVersion": r.triage_rule_version, "triageExplanation": r.triage_explanation,
        "source": r.source, "sourceType": r.source_type, "verificationStatus": r.verification_status,
        "evidenceLabel": evidence_label(r), "isDemo": r.is_demo, "version": r.version,
        "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
    }


def evidence_label(r: DiseaseReport) -> str:
    if r.verification_status == "LAB_CONFIRMED":
        return "LAB CONFIRMED"
    if r.verification_status == "VERIFIED":
        return "VETERINARIAN VERIFIED"
    if r.verification_status == "REJECTED":
        return "NOT CONFIRMED"
    if r.status in ("ASSIGNED", "VISIT_SCHEDULED", "VISITED", "SAMPLE_COLLECTED", "LAB_TESTING", "RESULT_AVAILABLE"):
        return "UNDER VERIFICATION"
    return "REPORTED"


async def submit_report(
    db: AsyncSession,
    req: DiseaseReportCreate,
    reporter: User,
    *,
    source: str = "LIVE",
    device_id: Optional[str] = None,
    report_id: Optional[str] = None,
    request=None,
) -> Dict[str, Any]:
    try:
        triage = TriageEngine.evaluate(req.species, req.symptoms, req.number_affected, req.number_dead, req.temperature, req.district, req.temperature_unit)
    except TemperatureError as e:
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEMPERATURE", "message": str(e)})

    now = datetime.utcnow()
    has_coords = req.lat is not None and req.lng is not None
    report = DiseaseReport(
        id=report_id or f"REP-{uuid.uuid4().hex[:10].upper()}",
        report_number=f"MH-{req.district[:3].upper()}-{now:%y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        user_id=reporter.id, reporter_name=reporter.full_name, reporter_role=reporter.role,
        species=req.species, number_affected=req.number_affected, number_dead=req.number_dead, symptoms=req.symptoms,
        temperature=triage["temperature_c"], temperature_c=triage["temperature_c"], temperature_unit_reported=triage["temperature_unit_reported"],
        district=req.district, taluka=req.taluka, village=req.village,
        lat=req.lat if has_coords else None, lng=req.lng if has_coords else None,
        location_status=(req.location_source or "USER_ENTERED") if has_coords else "LOCATION_UNAVAILABLE",
        suspected_disease=req.suspected_disease or "Unknown", status="SUBMITTED",
        triage_urgency=triage["urgency"], triage_risk_level=triage["risk_level"], triage_recommendations=triage["recommended_actions"],
        triage_confidence=triage["confidence"], triage_rule_version=triage["rule_version"], triage_explanation=triage["explanation"],
        source_type=SOURCE_TYPES.get(reporter.role, "OFFICIAL_FIELD_REPORT"),
        verification_status="UNVERIFIED",
        notes=req.notes, source=source, is_demo=bool(reporter.is_demo), client_id=req.client_id,
        updated_by=reporter.id, device_id=device_id, version=1,
        reported_at=(req.observed_at.replace(tzinfo=None) if req.observed_at else now),
    )
    db.add(report)
    record_transition(db, "REPORT", report.id, None, "SUBMITTED", reporter)
    transition(db, "REPORT", report, "TRIAGED", reporter, note=f"rule triage {triage['rule_version']}: {triage['risk_level']}")

    created_case: Optional[VeterinaryCase] = None
    offered: Optional[Dict[str, Any]] = None
    if triage["requires_vet"]:
        created_case = VeterinaryCase(
            id=f"CASE-{uuid.uuid4().hex[:10].upper()}",
            case_number=f"CAS-{req.district[:3].upper()}-{now:%y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            report_id=report.id, farmer_id=reporter.id if reporter.role == UserRole.FARMER.value else None,
            status="REPORTED", priority=triage["risk_level"], species=req.species, district=req.district, taluka=req.taluka,
            village=req.village, lat=report.lat, lng=report.lng, requires_lab=triage["requires_lab"], is_demo=report.is_demo,
            reported_problem=f"{len(req.symptoms)} symptom(s): {', '.join(req.symptoms)[:900]}",
            risk_score={"CRITICAL": 85.0, "HIGH": 65.0, "MODERATE": 40.0}.get(triage["risk_level"], 20.0),
        )
        db.add(created_case)
        await db.flush()
        record_transition(db, "CASE", created_case.id, None, "REPORTED", reporter)
        offered = await DispatchEngine.offer_next(db, created_case, reporter)
        if offered:
            transition(db, "REPORT", report, "ASSIGNED", reporter, note=f"case {created_case.case_number} offered to vet")
            vet = await db.get(User, offered["vet_id"])
            await NotificationService.queue(db, channel="SMS", template="VETERINARIAN_ASSIGNED", context={"case_number": created_case.case_number}, user=vet,
                                            dedup_key=f"vet-assigned:{created_case.id}:{vet.id}", require_consent=False)

    alert = None
    if triage["risk_level"] in ("HIGH", "CRITICAL"):
        alert, _ = await raise_alert(
            db, alert_type="CRITICAL_REPORT" if triage["risk_level"] == "CRITICAL" else "HIGH_RISK_REPORT",
            severity=triage["risk_level"],
            title=f"{triage['risk_level']} risk report – {req.district} – {req.suspected_disease or 'syndromic signs'}",
            message=f"{req.number_affected} {req.species} affected ({req.number_dead} deaths) in {req.village}, {req.district}. Unverified farmer/field report; veterinary verification pending.",
            dedup_key=f"report:{req.district}:{req.village}:{(req.suspected_disease or 'unknown').lower()}:{now:%Y%m%d}",
            district=req.district, taluka=req.taluka, disease=req.suspected_disease,
            target_roles=["VETERINARIAN", "DISTRICT_OFFICER", "BLOCK_OFFICER", "STATE_OFFICER"],
            related_entity_type="REPORT", related_entity_id=report.id, evidence_level="REPORTED", is_demo=report.is_demo,
        )

    await NotificationService.queue(db, channel="IN_APP", template="REPORT_RECEIVED", context={"report_number": report.report_number, "risk": triage["risk_level"]}, user=reporter)
    await AuditService.for_user(db, reporter, "DISEASE_REPORT_SUBMITTED", "REPORT", report.id, request=request, commit=False,
                                new_value={"district": report.district, "species": report.species, "triage": triage["risk_level"], "source": source})
    await db.commit()

    events = [Event("report.created", {"id": report.id, "reportNumber": report.report_number, "species": report.species, "district": report.district,
                                       "village": report.village, "riskLevel": report.triage_risk_level, "disease": report.suspected_disease,
                                       "evidenceLabel": "REPORTED", "created_at": report.created_at.isoformat()}, district=report.district, taluka=report.taluka, owner_id=reporter.id),
              Event("report.triaged", {"id": report.id, "riskLevel": triage["risk_level"], "ruleVersion": triage["rule_version"]}, district=report.district, owner_id=reporter.id)]
    if created_case:
        events.append(Event("case.created", {"id": created_case.id, "caseNumber": created_case.case_number, "district": created_case.district,
                                             "status": created_case.status, "assignedVetId": created_case.assigned_vet_id}, district=created_case.district, owner_id=reporter.id,
                            user_ids=[offered["vet_id"]] if offered else []))
        if offered:
            events.append(Event("vet.assigned", {"caseId": created_case.id, "vetId": offered["vet_id"]}, user_ids=[offered["vet_id"], reporter.id]))
    if alert:
        events.append(Event("alert.created", {"id": alert.id, "severity": alert.severity, "title": alert.title, "district": alert.district}, district=alert.district))
    for ev in events:
        await ev.publish()

    return {
        "success": True,
        "report": {"id": report.id, "reportNumber": report.report_number, "trackingId": report.report_number, "status": report.status,
                   "district": report.district, "village": report.village, "species": report.species, "locationStatus": report.location_status,
                   "evidenceLabel": evidence_label(report)},
        "triage": triage,
        "assignedCase": ({"caseId": created_case.id, "caseNumber": created_case.case_number, "status": created_case.status,
                          "assignedVet": ({k: offered[k] for k in ("vet_id", "full_name", "district", "distance_km", "distance_basis", "eta_status", "location_status")} if offered else None),
                          "dispatchStatus": "OFFERED" if offered else "NO_ELIGIBLE_VET_ESCALATED"} if created_case else None),
    }
