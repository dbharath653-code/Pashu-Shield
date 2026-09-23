"""State machines for reports, veterinary cases and lab samples.

Every transition is validated against an explicit graph and persisted as a WorkflowEvent.
Legacy labels sent by existing UI screens ("En Route", "Closed", "Testing", ...) are
normalised to canonical states so the API contract stays compatible.
"""
from __future__ import annotations

import uuid
from typing import Dict, Optional, Set

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import WorkflowEvent

REPORT_TRANSITIONS: Dict[str, Set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"TRIAGED", "CLOSED"},
    "TRIAGED": {"ASSIGNED", "RESOLVED", "CLOSED"},
    "ASSIGNED": {"VISIT_SCHEDULED", "VISITED", "TRIAGED", "CLOSED"},
    "VISIT_SCHEDULED": {"VISITED", "ASSIGNED", "CLOSED"},
    "VISITED": {"SAMPLE_COLLECTED", "VERIFIED", "RESOLVED"},
    "SAMPLE_COLLECTED": {"LAB_TESTING"},
    "LAB_TESTING": {"RESULT_AVAILABLE"},
    "RESULT_AVAILABLE": {"VERIFIED"},
    "VERIFIED": {"RESOLVED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}

CASE_TRANSITIONS: Dict[str, Set[str]] = {
    "REPORTED": {"TRIAGED", "ASSIGNED", "CLOSED"},
    "TRIAGED": {"ASSIGNED", "CLOSED"},
    "ASSIGNED": {"ACCEPTED", "REJECTED", "TRIAGED", "CLOSED"},
    "REJECTED": {"ASSIGNED", "TRIAGED"},
    "ACCEPTED": {"EN_ROUTE", "ON_SITE", "ASSIGNED"},
    "EN_ROUTE": {"ON_SITE"},
    "ON_SITE": {"UNDER_EXAMINATION"},
    "UNDER_EXAMINATION": {"TREATMENT", "LAB_REQUIRED", "RESOLVED"},
    "TREATMENT": {"LAB_REQUIRED", "FOLLOW_UP", "RESOLVED"},
    "LAB_REQUIRED": {"TREATMENT", "FOLLOW_UP", "RESOLVED"},
    "FOLLOW_UP": {"TREATMENT", "RESOLVED"},
    "RESOLVED": {"CLOSED", "FOLLOW_UP"},
    "CLOSED": set(),
}

SAMPLE_TRANSITIONS: Dict[str, Set[str]] = {
    "COLLECTED": {"IN_TRANSIT", "RECEIVED", "REJECTED"},
    "IN_TRANSIT": {"RECEIVED", "REJECTED"},
    "RECEIVED": {"ACCEPTED", "REJECTED"},
    "ACCEPTED": {"TESTING"},
    "TESTING": {"RESULT_PENDING"},
    "RESULT_PENDING": {"VERIFIED", "TESTING"},
    "VERIFIED": {"RELEASED", "RESULT_PENDING"},  # correction re-opens with a versioned revision
    "RELEASED": {"CLOSED", "RESULT_PENDING"},
    "REJECTED": {"CLOSED"},
    "CLOSED": set(),
}

GRAPHS = {"REPORT": REPORT_TRANSITIONS, "CASE": CASE_TRANSITIONS, "SAMPLE": SAMPLE_TRANSITIONS}

_ALIASES = {
    # case labels used by VetResponseContext
    "PENDING": "REPORTED", "EN ROUTE": "EN_ROUTE", "UNDER EXAMINATION": "UNDER_EXAMINATION",
    "TREATMENT ACTIVE": "TREATMENT", "ON SITE": "ON_SITE", "LAB REQUIRED": "LAB_REQUIRED", "FOLLOW UP": "FOLLOW_UP",
    # sample labels used by LabContext
    "IN TRANSIT": "IN_TRANSIT", "RESULT PENDING": "RESULT_PENDING",
    # legacy report labels
    "SUSPECTED": "SUBMITTED", "INVESTIGATING": "ASSIGNED", "CONFIRMED": "VERIFIED",
}


def normalize_status(value: str) -> str:
    key = (value or "").strip().upper().replace("-", " ")
    key = _ALIASES.get(key, key)
    return key.replace(" ", "_")


def can_transition(entity: str, current: Optional[str], target: str) -> bool:
    graph = GRAPHS[entity]
    cur = normalize_status(current or "")
    tgt = normalize_status(target)
    if cur == tgt:
        return True  # idempotent re-send (common with offline retries)
    return tgt in graph.get(cur, set())


def assert_transition(entity: str, current: Optional[str], target: str) -> str:
    tgt = normalize_status(target)
    if tgt not in GRAPHS[entity]:
        raise HTTPException(status_code=422, detail={"code": "UNKNOWN_STATUS", "message": f"Unknown {entity.lower()} status '{target}'"})
    if not can_transition(entity, current, tgt):
        allowed = sorted(GRAPHS[entity].get(normalize_status(current or ""), set()))
        raise HTTPException(status_code=409, detail={
            "code": "INVALID_STATUS_TRANSITION",
            "message": f"Cannot move {entity.lower()} from {normalize_status(current or '')} to {tgt}. Allowed: {', '.join(allowed) or 'none (terminal state)'}",
        })
    return tgt


def record_transition(db: AsyncSession, entity: str, entity_id: str, from_status: Optional[str], to_status: str, actor=None, note: Optional[str] = None) -> None:
    db.add(WorkflowEvent(
        id=uuid.uuid4().hex, entity_type=entity, entity_id=entity_id,
        from_status=normalize_status(from_status) if from_status else None, to_status=normalize_status(to_status),
        actor_id=getattr(actor, "id", None), actor_role=getattr(actor, "role", None), note=note,
    ))


def transition(db: AsyncSession, entity: str, obj, target: str, actor=None, note: Optional[str] = None) -> str:
    """Validate + apply + record. Returns the canonical new status."""
    current = obj.status
    new_status = assert_transition(entity, current, target)
    if normalize_status(current or "") != new_status:
        obj.status = new_status
        if hasattr(obj, "version") and obj.version is not None:
            obj.version += 1
        record_transition(db, entity, obj.id, current, new_status, actor, note)
    return new_status
