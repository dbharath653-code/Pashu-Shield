"""Real Twilio provider: webhook signature validation (official RequestValidator),
outbound REST calls for veterinarian dialling, and authenticated recording download."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import httpx
from twilio.request_validator import RequestValidator

from backend.config import settings
from backend.services.telephony.base import TelephonyProvider, WebhookVerificationError

logger = logging.getLogger("pashu_shield.telephony")


class TwilioProvider(TelephonyProvider):
    name = "twilio"
    is_mock = False

    def _validator(self) -> Optional[RequestValidator]:
        token = settings.TWILIO_AUTH_TOKEN or settings.TWILIO_WEBHOOK_SECRET
        if not token:
            return None
        return RequestValidator(token)

    # ---- inbound ---------------------------------------------------------------------------
    def validate_webhook(self, raw_body: bytes, params: Dict[str, str], signature: Optional[str], url: str) -> None:
        if not settings.TWILIO_VALIDATE_WEBHOOK:
            return
        validator = self._validator()
        if validator is None:
            # Fail closed: validation is enabled but no token/secret is configured.
            raise WebhookVerificationError("webhook validation enabled but TWILIO_AUTH_TOKEN is not configured")
        if not signature:
            raise WebhookVerificationError("missing X-Twilio-Signature header")
        # RequestValidator computes HMAC-SHA1 over the full URL + POST params (official algorithm).
        if not validator.validate(url, params, signature):
            raise WebhookVerificationError("invalid X-Twilio-Signature")

    def get_call_sid(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("CallSid") or params.get("callSid")

    def get_caller_number(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("From") or params.get("from")

    # ---- capabilities ----------------------------------------------------------------------
    @property
    def supports_outbound(self) -> bool:
        return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)

    @property
    def supports_recording(self) -> bool:
        return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)

    # ---- outbound ---------------------------------------------------------------------------
    async def place_outbound_call(self, to_number: str, webhook_url: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        if not self.supports_outbound:
            return {"ok": False, "provider_call_id": None, "error": "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not configured"}
        sid, token = settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
        data: Dict[str, Any] = {
            "To": to_number,
            "From": settings.TWILIO_PHONE_NUMBER,
            "Url": webhook_url,
            "Method": "POST",
        }
        if status_callback:
            data["StatusCallback"] = status_callback
            data["StatusCallbackMethod"] = "POST"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data=data, auth=(sid, token))
            body = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and body.get("sid"):
                return {"ok": True, "provider_call_id": body["sid"], "error": None}
            err = str(body.get("message") or f"HTTP {resp.status_code}")[:300]
            logger.warning("twilio outbound call failed", extra={"fields": {"error": err}})
            return {"ok": False, "provider_call_id": None, "error": err}
        except httpx.HTTPError as e:
            logger.warning("twilio outbound call error", extra={"fields": {"error": type(e).__name__}})
            return {"ok": False, "provider_call_id": None, "error": type(e).__name__}

    # ---- recordings ---------------------------------------------------------------------------
    async def download_recording(self, recording_url: str) -> Tuple[bytes, str]:
        """Twilio recording URLs require HTTP basic auth with the account credentials.
        The bytes are only ever returned through an RBAC-checked, audited endpoint."""
        if not self.supports_outbound:
            raise WebhookVerificationError("Twilio credentials not configured")
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(recording_url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))
            resp.raise_for_status()
            return resp.content, resp.headers.get("content-type", "audio/mpeg")
