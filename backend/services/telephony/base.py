"""Abstract telephony provider interface.

Pashu Shield's IVR business logic talks to this interface only. A provider adapts one
telephony transport (Exotel today) to it: webhook verification, reading the identity and
input fields the provider sends, optional call-id verification, and private recording access.

Every operation below has a caller in the codebase — nothing speculative is declared.

  * ``markup_dialect``      – which voice-markup renderer answers this provider (``exoml``)
  * ``validate_webhook``    – trust check for an inbound provider request
  * ``verify_call_id``      – optional authenticated confirmation that a call id is ours
  * ``get_call_id``         – the provider's unique call identifier (Exotel ``CallSid``)
  * ``get_caller_number`` / ``get_called_number`` / ``get_direction``
  * ``get_digits``          – DTMF collected by a ``<Gather>``
  * ``get_dial_result``     – outcome of a bridged leg (Exotel ``DialCallStatus``)
  * ``get_provider_status`` / ``get_recording_url`` – terminal-status callback fields
  * ``download_recording``  – private, audited recording access

Outbound dialling to a veterinarian is *not* on this interface: PATH A bridges the legs
with an ExoML ``<Dial>`` inside the live call, so there is no outbound REST call to make.
Adding one when it is needed is a one-method change here.
"""
from __future__ import annotations

import abc
from typing import Dict, Optional, Tuple


class WebhookVerificationError(Exception):
    """Webhook could not be trusted (bad/missing secret, unverifiable call id)."""


class TelephonyProvider(abc.ABC):
    name: str = "base"
    is_mock: bool = False
    #: key into services/telephony/markup.RENDERERS
    markup_dialect: str = ""
    #: header a direct (non-provider) caller may use instead of the URL token
    secret_header: str = "X-Webhook-Secret"
    #: DTMF plus speech gather is not universally available; ExoML is DTMF only.
    supports_speech_input: bool = False

    # ---- inbound ---------------------------------------------------------------------------
    @abc.abstractmethod
    def validate_webhook(self, raw_body: bytes, params: Dict[str, str],
                         secret: Optional[str]) -> None:
        """Raise WebhookVerificationError when the request cannot be trusted."""

    async def verify_call_id(self, call_id: str) -> bool:
        """Authenticated confirmation that `call_id` belongs to our provider account.
        Providers without such an API return False; callers treat that as "unverified"."""
        return False

    @abc.abstractmethod
    def get_call_id(self, params: Dict[str, str]) -> Optional[str]:
        """Provider-unique call identifier used for idempotency (Exotel: ``CallSid``)."""

    @abc.abstractmethod
    def get_caller_number(self, params: Dict[str, str]) -> Optional[str]:
        ...

    def get_called_number(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("To") or params.get("to")

    def get_direction(self, params: Dict[str, str]) -> Optional[str]:
        return params.get("Direction") or params.get("direction")

    def get_digits(self, params: Dict[str, str]) -> str:
        """DTMF collected by the previous gather ("" when there was no input)."""
        return ""

    def get_dial_result(self, params: Dict[str, str]) -> str:
        """Outcome of a bridged leg, lower-cased ("" when this is not a dial callback)."""
        return ""

    def get_provider_status(self, params: Dict[str, str]) -> str:
        """Overall call status from a terminal-status callback, lower-cased."""
        return ""

    def get_recording_url(self, params: Dict[str, str]) -> Optional[str]:
        return None

    # ---- recordings (private access only) ----------------------------------------------------
    async def download_recording(self, recording_url: str) -> Tuple[bytes, str]:
        """Fetch recording bytes for authorised, audited access. Never expose the URL publicly."""
        raise NotImplementedError(f"{self.name} cannot download recordings")


__all__ = ["TelephonyProvider", "WebhookVerificationError"]
