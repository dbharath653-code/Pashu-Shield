"""Call state machine for CallSession.status.

Explicit states (see backend/models.py::CallSession):
    INBOUND, IDENTIFIED, LANGUAGE_SELECTED, MENU_SELECTED, VET_SEARCH, VET_DIALING,
    VET_CONNECTED, BRIDGED, SURVEY, CONFIRMATION, REPORT_CREATED, TRIAGED,
    CASE_STATUS, CALLBACK_REQUESTED, COMPLETED, FAILED

Handles busy / no-answer / timeout / rejected / provider failure / farmer disconnect /
vet disconnect / duplicate webhook / provider retry:
  * transitions are validated — illegal jumps are logged and ignored (state never regresses),
  * duplicate webhooks find the existing session by provider_call_id (webhook_service),
  * provider status strings (Exotel Status / DialCallStatus) map onto terminal states
    idempotently.
"""
from __future__ import annotations

import logging
from typing import Dict, FrozenSet, Optional

logger = logging.getLogger("pashu_shield.telephony")

INBOUND = "INBOUND"
IDENTIFIED = "IDENTIFIED"
LANGUAGE_SELECTED = "LANGUAGE_SELECTED"
MENU_SELECTED = "MENU_SELECTED"
VET_SEARCH = "VET_SEARCH"
VET_DIALING = "VET_DIALING"
VET_CONNECTED = "VET_CONNECTED"
BRIDGED = "BRIDGED"
SURVEY = "SURVEY"
CONFIRMATION = "CONFIRMATION"
REPORT_CREATED = "REPORT_CREATED"
TRIAGED = "TRIAGED"
CASE_STATUS = "CASE_STATUS"
CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
COMPLETED = "COMPLETED"
FAILED = "FAILED"

ALL_STATES: FrozenSet[str] = frozenset({
    INBOUND, IDENTIFIED, LANGUAGE_SELECTED, MENU_SELECTED, VET_SEARCH, VET_DIALING,
    VET_CONNECTED, BRIDGED, SURVEY, CONFIRMATION, REPORT_CREATED, TRIAGED, CASE_STATUS,
    CALLBACK_REQUESTED, COMPLETED, FAILED,
})

# Directed transitions. COMPLETED/FAILED are terminal (idempotent re-entry allowed).
TRANSITIONS: Dict[str, FrozenSet[str]] = {
    INBOUND: frozenset({IDENTIFIED, LANGUAGE_SELECTED, MENU_SELECTED, SURVEY, FAILED, COMPLETED}),
    IDENTIFIED: frozenset({LANGUAGE_SELECTED, MENU_SELECTED, VET_SEARCH, SURVEY, FAILED, COMPLETED}),
    LANGUAGE_SELECTED: frozenset({MENU_SELECTED, VET_SEARCH, VET_DIALING, SURVEY, FAILED, COMPLETED}),
    MENU_SELECTED: frozenset({VET_SEARCH, VET_DIALING, SURVEY, CASE_STATUS, LANGUAGE_SELECTED,
                              CALLBACK_REQUESTED, FAILED, COMPLETED}),
    CASE_STATUS: frozenset({MENU_SELECTED, SURVEY, CALLBACK_REQUESTED, COMPLETED, FAILED}),
    VET_SEARCH: frozenset({VET_DIALING, SURVEY, FAILED, COMPLETED}),
    VET_DIALING: frozenset({VET_CONNECTED, VET_DIALING, SURVEY, LANGUAGE_SELECTED, FAILED, COMPLETED}),
    VET_CONNECTED: frozenset({BRIDGED, SURVEY, FAILED, COMPLETED}),
    BRIDGED: frozenset({SURVEY, CONFIRMATION, REPORT_CREATED, FAILED, COMPLETED}),
    SURVEY: frozenset({CONFIRMATION, REPORT_CREATED, CALLBACK_REQUESTED, MENU_SELECTED, FAILED, COMPLETED}),
    CONFIRMATION: frozenset({REPORT_CREATED, SURVEY, FAILED, COMPLETED}),
    REPORT_CREATED: frozenset({TRIAGED, CALLBACK_REQUESTED, COMPLETED, FAILED}),
    TRIAGED: frozenset({CALLBACK_REQUESTED, COMPLETED, FAILED}),
    CALLBACK_REQUESTED: frozenset({COMPLETED, FAILED}),
    COMPLETED: frozenset({COMPLETED}),
    FAILED: frozenset({FAILED}),
}

# Exotel call status (StatusCallback `Status` / ExoML `DialCallStatus`) -> our states,
# applied idempotently. Exotel emits: queued, ringing, in-progress, completed, failed,
# busy, no-answer, canceled.
PROVIDER_STATUS_MAP: Dict[str, str] = {
    "queued": INBOUND,
    "ringing": INBOUND,
    "in-progress": IDENTIFIED,  # answered; the IVR flow advances it further
    "busy": FAILED,
    "failed": FAILED,
    "no-answer": FAILED,
    "canceled": FAILED,
    "completed": COMPLETED,
}


def can_transition(current: Optional[str], target: str) -> bool:
    current = (current or INBOUND).upper()
    target = target.upper()
    if target not in ALL_STATES:
        return False
    if current == target:
        return True  # duplicate webhook / retry: idempotent
    return target in TRANSITIONS.get(current, frozenset())


def apply_transition(session, target: str, *, reason: str = "") -> bool:
    """Validate + apply a state transition on a CallSession-like object.
    Returns True when the state changed; illegal transitions are logged and ignored
    (the first-seen state wins — a late 'ringing' cannot regress a COMPLETED call)."""
    current = (session.status or INBOUND).upper()
    target = target.upper()
    if not can_transition(current, target):
        logger.warning(
            "illegal call state transition ignored",
            extra={"fields": {"call_session": getattr(session, "id", None), "from": current, "to": target, "reason": reason}},
        )
        return False
    if current == target:
        return False
    session.status = target
    logger.info(
        "call state transition",
        extra={"fields": {"call_session": getattr(session, "id", None), "from": current, "to": target, "reason": reason}},
    )
    return True


def is_terminal(status: Optional[str]) -> bool:
    return (status or "").upper() in {COMPLETED, FAILED}


def active_states() -> FrozenSet[str]:
    return ALL_STATES - {COMPLETED, FAILED}
