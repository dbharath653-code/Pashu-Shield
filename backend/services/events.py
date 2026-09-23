"""Standardised real-time events. Only backend code publishes; payload schema:
    {"type": "<legacy UPPER_SNAKE>", "event": "<domain.event>", "id": uuid, "ts": iso, "data": {...}, "<legacy key>": {...}}
Legacy `type`/top-level keys are kept so existing frontend listeners keep working.
Delivery is filtered per connection by role, jurisdiction and ownership (see websocket_manager).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

EVENT_NAMES = {
    "report.created": ("REPORT_CREATED", "report"),
    "report.triaged": ("REPORT_TRIAGED", "report"),
    "report.verified": ("REPORT_VERIFIED", "report"),
    "case.created": ("CASE_CREATED", "case"),
    "case.status_changed": ("CASE_STATUS_CHANGED", "case"),
    "vet.assigned": ("VET_ASSIGNED", "dispatch"),
    "vet.accepted": ("VET_ACCEPTED", "dispatch"),
    "vet.rejected": ("VET_REJECTED", "dispatch"),
    "sample.collected": ("SAMPLE_COLLECTED", "sample"),
    "sample.status_changed": ("SAMPLE_STATUS_CHANGED", "sample"),
    "sample.received": ("SAMPLE_RECEIVED", "sample"),
    "lab.result_available": ("LAB_RESULT_AVAILABLE", "sample"),
    "lab.result_verified": ("LAB_RESULT_VERIFIED", "sample"),
    "outbreak.detected": ("OUTBREAK_DETECTED", "cluster"),
    "alert.created": ("ALERT_CREATED", "alert"),
    "notification.sent": ("NOTIFICATION_SENT", "notification"),
    "sync.completed": ("SYNC_COMPLETED", "sync"),
    # --- Inbound IVR / telephony (delivered over the existing WebSocket manager) ---------
    "call.started": ("CALL_STARTED", "call"),
    "call.language_selected": ("CALL_LANGUAGE_SELECTED", "call"),
    "call.vet_search_started": ("CALL_VET_SEARCH_STARTED", "call"),
    "call.vet_found": ("CALL_VET_FOUND", "call"),
    "call.vet_dialing": ("CALL_VET_DIALING", "call"),
    "call.vet_connected": ("CALL_VET_CONNECTED", "call"),
    "call.vet_unavailable": ("CALL_VET_UNAVAILABLE", "call"),
    "call.survey_started": ("CALL_SURVEY_STARTED", "call"),
    "call.survey_answered": ("CALL_SURVEY_ANSWERED", "call"),
    "call.survey_completed": ("CALL_SURVEY_COMPLETED", "call"),
    "call.transcript_updated": ("CALL_TRANSCRIPT_UPDATED", "call"),
    "call.summary_updated": ("CALL_SUMMARY_UPDATED", "call"),
    "call.report_created": ("CALL_REPORT_CREATED", "call"),
    "call.triaged": ("CALL_TRIAGED", "call"),
    "call.callback_requested": ("CALL_CALLBACK_REQUESTED", "call"),
    "call.callback_updated": ("CALL_CALLBACK_UPDATED", "call"),
    "call.completed": ("CALL_COMPLETED", "call"),
}


@dataclass
class Event:
    name: str
    data: Dict[str, Any]
    district: Optional[str] = None
    taluka: Optional[str] = None
    owner_id: Optional[str] = None
    user_ids: List[str] = field(default_factory=list)
    roles: Optional[List[str]] = None

    def message(self) -> Dict[str, Any]:
        legacy_type, legacy_key = EVENT_NAMES[self.name]
        return {"type": legacy_type, "event": self.name, "id": uuid.uuid4().hex, "ts": datetime.utcnow().isoformat(), "data": self.data, legacy_key: self.data}

    async def publish(self) -> None:
        from backend.services.websocket_manager import ws_manager
        await ws_manager.publish(self)
