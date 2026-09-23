"""Abstract telephony provider interface.

Operations map 1:1 to what the IVR flow needs:
  * validate_webhook  – provider signature check (Twilio X-Twilio-Signature / shared secret)
  * get_call_sid / get_caller_number – read identity fields from the webhook form
  * place_outbound_call – PATH A veterinarian dialling (abstracted REST call)
  * supports_outbound / supports_recording – capability flags (trial accounts, mock)
  * recording_auth / download_recording – private, audited recording access
"""
from __future__ import annotations

import abc
from typing import Any, Dict, Optional, Tuple


class WebhookVerificationError(Exception):
    """Webhook signature/secret verification failed."""


class TelephonyProvider(abc.ABC):
    name: str = "base"
    is_mock: bool = False

    # ---- inbound ---------------------------------------------------------------------------
    @abc.abstractmethod
    def validate_webhook(self, raw_body: bytes, params: Dict[str, str], signature: Optional[str], url: str) -> None:
        """Raise WebhookVerificationError when the request cannot be trusted."""

    @abc.abstractmethod
    def get_call_sid(self, params: Dict[str, str]) -> Optional[str]:
        ...

    @abc.abstractmethod
    def get_caller_number(self, params: Dict[str, str]) -> Optional[str]:
        ...

    def get_called_number(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("To") or params.get("to")

    # ---- capabilities ----------------------------------------------------------------------
    @property
    def supports_outbound(self) -> bool:
        return False

    @property
    def supports_recording(self) -> bool:
        return False

    # ---- outbound (PATH A: veterinarian dial) ----------------------------------------------
    async def place_outbound_call(self, to_number: str, webhook_url: str, status_callback: Optional[str] = None) -> Dict[str, Any]:
        """Start an outbound call that fetches `webhook_url` for its TwiML.
        Returns {"ok": bool, "provider_call_id": str|None, "error": str|None}."""
        return {"ok": False, "provider_call_id": None, "error": f"{self.name} does not support outbound calls"}

    # ---- recordings (private access only) ----------------------------------------------------
    async def download_recording(self, recording_url: str) -> Tuple[bytes, str]:
        """Fetch recording bytes for authorised, audited access. Never expose the URL publicly."""
        raise NotImplementedError(f"{self.name} cannot download recordings")
