"""Mock telephony provider — complete IVR testing without a real telephone call.

Used by:
  * automated tests (full INBOUND -> LANGUAGE -> MENU -> SURVEY -> REPORT -> TRIAGE ->
    CALLBACK flow, and the veterinarian-bridge branch),
  * ``DEMO_MODE`` "Simulate Incoming Farmer Call" (sessions are flagged ``is_simulated=True``
    and always labelled DEMO / SIMULATED — never presented as a real Exotel call).

The mock subclasses :class:`ExotelProvider` because it speaks exactly the same wire format
and reads exactly the same Exotel parameter names (``CallSid``, ``From``, ``To``, ``digits``,
``DialCallStatus``, ``Status``) — so tests exercise the production parsing path. Only the
trust check and the recording bytes are simulated, and both are labelled as such.
"""
from __future__ import annotations

import hashlib
import hmac
import struct
import uuid
from typing import Dict, Optional, Tuple

from backend.config import settings
from backend.services.telephony.base import WebhookVerificationError
from backend.services.telephony.exotel_provider import ExotelProvider

# 8kHz mono 8-bit silence: a clearly synthetic recording, never passed off as real audio.
_SILENCE_SAMPLES = 8000


class MockTelephonyProvider(ExotelProvider):
    name = "mock"
    is_mock = True
    secret_header = "X-Mock-Signature"

    def validate_webhook(self, raw_body: bytes, params: Dict[str, str], secret: Optional[str]) -> None:
        expected = settings.EXOTEL_WEBHOOK_SECRET
        if not expected:
            return  # mock: no shared secret configured -> open (tests / local demo)
        # Either the ExoML-style URL token, or an HMAC over the canonical body so a raw
        # replayed webhook can be exercised in tests.
        if secret and hmac.compare_digest(expected.strip(), secret.strip()):
            return
        body_signature = params.get("MockSignature")
        if body_signature and hmac.compare_digest(
                hmac.new(expected.encode(), raw_body, hashlib.sha256).hexdigest(), body_signature):
            return
        raise WebhookVerificationError("invalid mock webhook secret")

    async def verify_call_id(self, call_id: str) -> bool:
        return bool(call_id)  # mock call ids are ours by construction

    async def download_recording(self, recording_url: str) -> Tuple[bytes, str]:
        header = (b"RIFF" + struct.pack("<I", 36 + _SILENCE_SAMPLES) + b"WAVEfmt "
                  + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 8000, 1, 8) + b"data"
                  + struct.pack("<I", _SILENCE_SAMPLES))
        return header + (b"\x80" * _SILENCE_SAMPLES), "audio/wav"


def mock_call_id() -> str:
    """Identifier shape used by the mock provider (never confused with a real CallSid)."""
    return f"MOCK-{uuid.uuid4().hex[:12].upper()}"


def mock_signature(raw_body: bytes) -> str:
    """Body-derived signature accepted by the mock provider when a shared secret is set."""
    return hmac.new(settings.EXOTEL_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()


__all__ = ["MockTelephonyProvider", "mock_call_id", "mock_signature", "WebhookVerificationError"]
