"""Mock telephony provider — complete IVR testing without a real telephone call.

Used by:
  * automated tests (full INBOUND -> LANGUAGE -> SURVEY -> REPORT -> TRIAGE -> CALLBACK flow)
  * DEMO_MODE "Simulate Incoming Farmer Call" (sessions are flagged is_simulated=True and
    always labelled DEMO / SIMULATED — never presented as a real Twilio call).

Webhook "signature" for the mock is a shared secret header `X-Mock-Signature` compared
constant-time against TWILIO_WEBHOOK_SECRET (when that secret is set).
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any, Dict, Optional, Tuple

from backend.config import settings
from backend.services.telephony.base import TelephonyProvider, WebhookVerificationError


class MockTelephonyProvider(TelephonyProvider):
    name = "mock"
    is_mock = True

    # Outbound IS supported in the mock: place_outbound_call records the attempt and
    # the call_router drives the no-answer/busy/answer scenario deterministically.
    @property
    def supports_outbound(self) -> bool:
        return True

    @property
    def supports_recording(self) -> bool:
        return True

    def validate_webhook(self, raw_body: bytes, params: Dict[str, str], signature: Optional[str], url: str) -> None:
        secret = settings.TWILIO_WEBHOOK_SECRET
        if not secret:
            return  # mock: no shared secret configured -> open (tests / local demo)
        if not signature:
            raise WebhookVerificationError("missing X-Mock-Signature header")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise WebhookVerificationError("invalid X-Mock-Signature")

    def get_call_sid(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("CallSid") or params.get("callSid") or params.get("MockCallId")

    def get_caller_number(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("From") or params.get("from")

    async def place_outbound_call(self, to_number: str, webhook_url: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        # Deterministic mock: the caller (call_router) decides answered/busy/no-answer from
        # the scenario attached to the CallSession — no network involved.
        return {"ok": True, "provider_call_id": f"MOCK-{uuid.uuid4().hex[:12].upper()}", "error": None}

    async def download_recording(self, recording_url: str) -> Tuple[bytes, str]:
        # Synthetic short WAV silence — mock recordings are labels, not real audio.
        # 44-byte header + 8000 samples of silence at 8kHz mono 8-bit.
        import struct

        data_size = 8000
        header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 8000, 1, 8) + b"data" + struct.pack("<I", data_size)
        return header + (b"\x80" * data_size), "audio/wav"
