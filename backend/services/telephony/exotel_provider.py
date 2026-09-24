"""Real Exotel telephony provider.

Implements the Exotel side of :class:`TelephonyProvider`:

* **Webhook trust.** Exotel does **not** sign ExoML or StatusCallback webhooks — there is
  no ``X-Exotel-Signature`` equivalent in the current API. Verification therefore uses the
  mechanisms Exotel actually supports, in this order:

  1. A shared secret carried in the URL we hand to Exotel (``?t=…``) and echoed back on
     every ExoML ``action`` request. Exotel will only ever POST to URLs that our own
     ExoML responses produced, so the token proves the request came from our configured
     ExoML application rather than from the internet. Compared in constant time.
  2. ``CallSid`` correlation: every follow-up request must reference a call session that
     an already-verified ``/ivr/incoming`` created (enforced by the router, not here).
  3. Optional ``EXOTEL_VERIFY_CALL_SID=true``: confirm the ``CallSid`` against Exotel's
     authenticated Call Details API. Off by default (one extra round trip per call);
     turn it on when you cannot keep the webhook token private.
  4. Network controls Exotel documents for webhooks: HTTPS only, plus an allow-list of
     Exotel's egress ranges at your ingress. See docs/EXOTEL_SETUP.md.

* **Authenticated REST.** Exotel APIs use HTTP Basic Auth — API Key as username, API Token
  as password, Account SID in the path
  (``https://<subdomain>/v1/Accounts/<account_sid>/…``).

* **Recordings.** ``RecordingUrl`` from a StatusCallback is an Exotel-hosted (pre-signed)
  object URL. It is fetched without our credentials — they must never be sent to a
  storage host — and the bytes are only ever returned through the RBAC-checked, audited
  dashboard endpoint.
"""
from __future__ import annotations

import hmac
import logging
import re
from typing import Dict, Optional, Tuple

import httpx

from backend.config import settings
from backend.services.telephony.base import TelephonyProvider, WebhookVerificationError

logger = logging.getLogger("pashu_shield.telephony")

# Exotel wraps the DTMF value in double quotes in several applet/webhook contexts
# (documented in Exotel's Gather applet reference) — strip them before parsing.
_QUOTES = re.compile(r'^\s*["\']?|["\']?\s*$')
# Only digits survive: the finish key ('#' / '*') is not part of an answer in any Pashu
# Shield IVR question, and a stray key must never make a valid choice look invalid.
_NON_DIGITS = re.compile(r"\D")

# StatusCallback / ExoML statuses Exotel emits.
EXOTEL_CALL_STATUSES = frozenset({
    "queued", "ringing", "in-progress", "completed", "failed", "busy", "no-answer", "canceled",
})


class ExotelProvider(TelephonyProvider):
    name = "exotel"
    is_mock = False
    markup_dialect = "exoml"
    secret_header = "X-Exotel-Webhook-Secret"
    # ExoML <Gather> collects DTMF only — the IVR keeps its keypad path as the real input.
    supports_speech_input = False

    # ---- credentials ------------------------------------------------------------------------
    @property
    def _credentials(self) -> Tuple[str, str]:
        return settings.EXOTEL_API_KEY, settings.EXOTEL_API_TOKEN

    @property
    def _api_base(self) -> str:
        return f"https://{settings.EXOTEL_SUBDOMAIN.strip('/')}/v1/Accounts/{settings.EXOTEL_ACCOUNT_SID}"

    @property
    def _configured(self) -> bool:
        return bool(settings.EXOTEL_API_KEY and settings.EXOTEL_API_TOKEN and settings.EXOTEL_ACCOUNT_SID)

    # ---- inbound: trust ----------------------------------------------------------------------
    def validate_webhook(self, raw_body: bytes, params: Dict[str, str], secret: Optional[str]) -> None:
        """Verify the shared webhook secret. Fails closed: when validation is enabled and
        no secret is configured, every request is rejected rather than accepted."""
        if not settings.EXOTEL_VALIDATE_WEBHOOK:
            return
        expected = settings.EXOTEL_WEBHOOK_SECRET
        if not expected:
            raise WebhookVerificationError(
                "webhook validation is enabled but EXOTEL_WEBHOOK_SECRET is not configured")
        if not secret:
            raise WebhookVerificationError(f"missing webhook secret ({self.secret_header} or ?t=)")
        if not hmac.compare_digest(expected.strip(), secret.strip()):
            raise WebhookVerificationError("invalid webhook secret")

    async def verify_call_id(self, call_id: str) -> bool:
        """Confirm `call_id` exists on our Exotel account via the authenticated Call
        Details API (``GET /v1/Accounts/<sid>/Calls/<CallSid>.json``)."""
        if not self._configured:
            logger.warning("EXOTEL_VERIFY_CALL_SID requested but Exotel credentials are not configured")
            return False
        if not call_id or len(call_id) > 64:
            return False
        url = f"{self._api_base}/Calls/{call_id}.json"
        try:
            async with httpx.AsyncClient(timeout=settings.EXOTEL_TIMEOUT_SECONDS) as client:
                resp = await client.get(url, auth=self._credentials)
        except httpx.HTTPError as exc:
            logger.warning("exotel call-id verification failed",
                           extra={"fields": {"error": type(exc).__name__}})
            return False
        if resp.status_code == 404:
            return False
        if resp.status_code != 200:
            logger.warning("exotel call-id verification unexpected status",
                           extra={"fields": {"status": resp.status_code}})
            return False
        try:
            body = resp.json()
        except ValueError:
            return False
        call = (body or {}).get("Call") or {}
        return str(call.get("Sid") or "") == call_id

    # ---- inbound: field extraction -----------------------------------------------------------
    def get_call_id(self, params: Dict[str, str]) -> Optional[str]:
        # Exotel uses CallSid for both ExoML requests and StatusCallback.
        raw = params.get("CallSid") or params.get("callSid") or params.get("callsid") or ""
        return raw.strip() or None

    def get_caller_number(self, params: Dict[str, str]) -> Optional[str]:
        return (params.get("From") or params.get("from") or "").strip() or None

    def get_called_number(self, params: Dict[str, str]) -> Optional[str]:
        return (params.get("To") or params.get("to") or "").strip() or None

    def get_direction(self, params: Dict[str, str]) -> Optional[str]:
        # Exotel: 'incoming' | 'outbound-dial' | 'outbound-api'
        return (params.get("Direction") or params.get("direction") or "").strip().lower() or None

    def get_digits(self, params: Dict[str, str]) -> str:
        """DTMF from the preceding ExoML ``<Gather>``.

        Exotel sends this as ``digits`` (lower-case) and may surround the value with double
        quotes; ``Digits`` is accepted too so a re-pointed flow or a direct API caller works.
        """
        raw = params.get("digits")
        if raw is None:
            raw = params.get("Digits")
        if raw is None:
            raw = params.get("input")
        if raw is None:
            return ""
        cleaned = _QUOTES.sub("", str(raw))
        return _NON_DIGITS.sub("", cleaned)[:32]

    def get_dial_result(self, params: Dict[str, str]) -> str:
        """Exotel sends ``DialCallStatus`` for the bridged leg after an ExoML ``<Dial>``."""
        raw = params.get("DialCallStatus") or params.get("dialCallStatus") or ""
        return str(raw).strip().lower()

    def get_provider_status(self, params: Dict[str, str]) -> str:
        raw = params.get("Status") or params.get("CallStatus") or params.get("status") or ""
        return str(raw).strip().lower()

    def get_recording_url(self, params: Dict[str, str]) -> Optional[str]:
        url = (params.get("RecordingUrl") or params.get("PreSignedRecordingUrl") or "").strip()
        return url if url.startswith("https://") else None

    # ---- recordings ---------------------------------------------------------------------------
    async def download_recording(self, recording_url: str) -> Tuple[bytes, str]:
        if not recording_url.startswith("https://"):
            raise WebhookVerificationError("refusing to fetch a non-HTTPS recording URL")
        try:
            async with httpx.AsyncClient(timeout=settings.EXOTEL_TIMEOUT_SECONDS, follow_redirects=True) as client:
                resp = await client.get(recording_url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("exotel recording download failed",
                           extra={"fields": {"error": type(exc).__name__}})
            raise WebhookVerificationError("recording could not be downloaded") from exc
        return resp.content, resp.headers.get("content-type", "audio/mpeg")

    # ---- diagnostics ---------------------------------------------------------------------------
    def configuration_error(self) -> Optional[str]:
        """Human-readable reason this provider cannot serve live calls, or None."""
        if not self._configured:
            return "EXOTEL_API_KEY / EXOTEL_API_TOKEN / EXOTEL_ACCOUNT_SID are not all configured"
        return None


__all__ = ["ExotelProvider", "EXOTEL_CALL_STATUSES"]
