"""Telephony provider abstraction.

Business logic in ``routers/`` and ``services/telephony/webhook_service.py`` depends only on
:class:`TelephonyProvider` and on the provider-neutral :class:`~backend.services.telephony.markup.VoiceDoc`.
Exotel-specific request parsing, webhook trust and REST calls live in ``ExotelProvider``;
``MockTelephonyProvider`` allows the complete test/demo path without a real call.

The voice markup renderer is selected by ``provider.markup_dialect``; importing
:mod:`backend.services.telephony.exoml` registers the ExoML renderer.
"""
from __future__ import annotations

from typing import Optional

from backend.config import settings
from backend.services.telephony import exoml  # noqa: F401  (registers the ExoML renderer)
from backend.services.telephony.base import TelephonyProvider, WebhookVerificationError
from backend.services.telephony.exotel_provider import ExotelProvider
from backend.services.telephony.mock_provider import MockTelephonyProvider

VALID_PROVIDERS = ("exotel", "mock")

_provider: Optional[TelephonyProvider] = None


def _build(name: str) -> TelephonyProvider:
    if name == "mock":
        return MockTelephonyProvider()
    return ExotelProvider()


def get_provider() -> TelephonyProvider:
    """Return the configured provider (``TELEPHONY_PROVIDER=exotel|mock``)."""
    global _provider
    wanted = settings.TELEPHONY_PROVIDER if settings.TELEPHONY_PROVIDER in VALID_PROVIDERS else "exotel"
    if _provider is None or _provider.name != wanted:
        _provider = _build(wanted)
    return _provider


def reset_provider() -> None:
    """Testing hook: drop the cached provider after settings change."""
    global _provider
    _provider = None


__all__ = [
    "TelephonyProvider",
    "WebhookVerificationError",
    "ExotelProvider",
    "MockTelephonyProvider",
    "get_provider",
    "reset_provider",
    "VALID_PROVIDERS",
]
