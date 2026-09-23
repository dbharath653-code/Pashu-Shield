"""Speech-to-text adapter for Twilio call recordings.

The existing Pashu Shield voice stack is browser Web Speech STT + the /voice/intent
parser — it cannot consume a Twilio recording URL, so this adapter securely downloads
the recording (provider-authenticated, never public) and optionally sends it to a
configured STT provider.

  STT_PROVIDER unset/none -> {"status": "NOT_CONFIGURED"} (no transcript is invented)
  STT_PROVIDER=openai_whisper + STT_API_KEY -> POST /v1/audio/transcriptions

If local Whisper is available in the deployment, set STT_PROVIDER=openai_whisper with a
compatible endpoint or extend this adapter — it is the single STT integration point.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from backend.config import settings

logger = logging.getLogger("pashu_shield.voice")

OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe_audio(audio: bytes, filename: str = "recording.wav",
                           content_type: str = "audio/wav") -> Dict[str, Any]:
    """Returns {"status": "COMPLETED"|"NOT_CONFIGURED"|"FAILED", "text": str|None, ...}."""
    provider = (settings.STT_PROVIDER or "").lower()
    if provider in ("", "none"):
        return {"status": "NOT_CONFIGURED", "text": None,
                "detail": "STT_PROVIDER is not configured; the recording was kept but not transcribed"}
    if not settings.STT_API_KEY:
        return {"status": "NOT_CONFIGURED", "text": None, "detail": "STT_API_KEY missing"}
    if provider == "openai_whisper":
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    OPENAI_TRANSCRIPTION_URL,
                    headers={"Authorization": f"Bearer {settings.STT_API_KEY}"},
                    files={"file": (filename, audio, content_type or "application/octet-stream")},
                    data={"model": "whisper-1", "response_format": "json"},
                )
            if resp.status_code == 200:
                body = resp.json()
                text = (body.get("text") or "").strip()
                return {"status": "COMPLETED" if text else "FAILED", "text": text or None,
                        "language": body.get("language")}
            logger.warning("stt provider error", extra={"fields": {"status": resp.status_code}})
            return {"status": "FAILED", "text": None, "detail": f"STT HTTP {resp.status_code}"}
        except httpx.HTTPError as e:
            return {"status": "FAILED", "text": None, "detail": type(e).__name__}
    return {"status": "NOT_CONFIGURED", "text": None, "detail": f"Unknown STT_PROVIDER {provider}"}
