"""Centralised TwiML generation.

Every voice endpoint returns `text/xml` TwiML produced here (never JSON), built with the
official `twilio` SDK's VoiceResponse so markup is always valid. Action/status URLs are
built from PUBLIC_API_BASE_URL when configured so they match the public https origin
Twilio signed.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin

from fastapi import Request
from twilio.twiml.voice_response import Dial, Gather, VoiceResponse

from backend.config import settings


def public_base_url(request: Optional[Request] = None) -> str:
    if settings.PUBLIC_API_BASE_URL:
        return settings.PUBLIC_API_BASE_URL.rstrip("/")
    if request is not None:
        return str(request.base_url).rstrip("/")
    return ""


def action_url(request: Optional[Request], path: str, query: str = "") -> str:
    """Absolute URL for a Twilio action/callback (e.g. /api/v1/telephony/ivr)."""
    base = public_base_url(request)
    url = urljoin(base + "/", path.lstrip("/"))
    return f"{url}?{query}" if query else url


def twiml_response(vr: VoiceResponse):
    """Render a VoiceResponse as a TwiML XML response with the correct content type."""
    from fastapi.responses import Response

    return Response(content=str(vr), media_type="application/xml")


def say(vr: VoiceResponse, text: str, language: Optional[str] = None, voice: Optional[str] = None, loop: int = 1):
    kwargs = {}
    if language:
        kwargs["language"] = _twilio_say_language(language)
    if voice:
        kwargs["voice"] = voice
    return vr.say(text, loop=loop, **kwargs)


def _twilio_say_language(language: str) -> str:
    """Map our language codes to Twilio <Say> language tags; fall back gracefully when
    Twilio speech synthesis has no voice for the code (architecture is kept: the selected
    language stays stored on the CallSession/IVRSurvey)."""
    lang = (language or "en").lower()
    exact = {
        "en": "en-US", "hi": "hi-IN", "mr": "mr-IN", "te": "te-IN",
        "kn": "kn-IN", "ta": "ta-IN", "gu": "gu-IN", "bn": "bn-IN",
    }
    return exact.get(lang, "en-US")


def gather_dtmf(request: Optional[Request], action_path: str, prompt: str, *, language: str = "en",
                query: str = "", num_digits: int = 1, finish_on_key: str = "#",
                timeout: int = 5, speech: bool = False, action: Optional[str] = None) -> Gather:
    """Build a <Gather> with a nested <Say> prompt (DTMF primary, speech optional secondary)."""
    kwargs = dict(
        action=action or action_url(request, action_path, query),
        method="POST",
        timeout=timeout,
        finishOnKey=finish_on_key,
    )
    if num_digits and num_digits > 0:
        kwargs["numDigits"] = num_digits
    if speech:
        kwargs["input"] = "dtmf speech"
        kwargs["speechTimeout"] = "auto"
        kwargs["language"] = _twilio_say_language(language)
    gather = Gather(**kwargs)
    say(gather, prompt, language=language)
    return gather


def dial_for(request: Optional[Request], vr: VoiceResponse, number: str, *, action_path: str,
             query: str = "", timeout: int = 20, caller_id: Optional[str] = None,
             recording: bool = False, status_callback_path: Optional[str] = None) -> Dial:
    kwargs = {
        "action": action_url(request, action_path, query),
        "method": "POST",
        "timeout": timeout,
    }
    if caller_id or settings.TWILIO_PHONE_NUMBER:
        kwargs["callerId"] = caller_id or settings.TWILIO_PHONE_NUMBER
    if recording and settings.CALL_RECORDING_ENABLED:
        kwargs["record"] = "record-from-answer"
    if status_callback_path:
        kwargs["statusCallback"] = action_url(request, status_callback_path)
        # TwiML attributes are strings: space-separated event list (a Python list would be repr()'d).
        kwargs["statusCallbackEvent"] = "initiated ringing answered completed"
        kwargs["statusCallbackMethod"] = "POST"
    dial = vr.dial(**kwargs)
    dial.number(number)
    return dial


def hangup(vr: VoiceResponse) -> None:
    vr.hangup()


def redirect_to(request: Optional[Request], vr: VoiceResponse, path: str, query: str = "") -> None:
    vr.redirect(url=action_url(request, path, query), method="POST")


def say_and_hangup(vr: VoiceResponse, text: str, language: str = "en") -> None:
    say(vr, text, language=language)
    hangup(vr)
