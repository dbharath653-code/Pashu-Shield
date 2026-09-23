"""Telephony provider abstraction.

Business logic in routers/ and webhook_service depends only on `TelephonyProvider`;
Twilio-specific request validation / outbound REST calls live in `TwilioProvider`,
and `MockTelephonyProvider` allows a complete test/demo path without any real call.

TwiML generation itself is provider-neutral (Twilio-compatible XML) and is centralised
in `backend/services/telephony/twiml.py`.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.config import settings
from backend.services.telephony.base import TelephonyProvider, WebhookVerificationError
from backend.services.telephony.mock_provider import MockTelephonyProvider
from backend.services.telephony.twilio_provider import TwilioProvider

_provider: Optional[TelephonyProvider] = None


def get_provider() -> TelephonyProvider:
    """Return the configured provider (TELEPHONY_PROVIDER=twilio|mock)."""
    global _provider
    wanted = "mock" if settings.TELEPHONY_PROVIDER == "mock" else "twilio"
    if _provider is None or _provider.name != wanted:
        _provider = MockTelephonyProvider() if wanted == "mock" else TwilioProvider()
    return _provider


def reset_provider() -> None:
    """Testing hook: drop the cached provider after settings change."""
    global _provider
    _provider = None


__all__ = [
    "TelephonyProvider",
    "WebhookVerificationError",
    "TwilioProvider",
    "MockTelephonyProvider",
    "get_provider",
    "reset_provider",
    "DescribeDict",
]

DescribeDict = Dict[str, Any]
