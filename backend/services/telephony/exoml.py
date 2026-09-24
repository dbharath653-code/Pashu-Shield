"""Exotel **ExoML** renderer.

ExoML (Exotel Markup Language) is the wire format Exotel expects back from an ExoML
application URL. It is *not* TwiML and the two are not interchangeable.

Verbs implemented here (the full set ExoML documents for programmable voice):

``<Response>``  root element
``<Say voice language loop>text</Say>``                  text-to-speech
``<Gather action method timeout finishOnKey numDigits>`` DTMF collection with a nested
                                                         ``<Say>``/``<Play>`` prompt
``<Dial action method timeout hangupOnStar timeLimit callerId record><Number>…``
``<Redirect method>url</Redirect>``                       URL is element *text*, not an attribute
``<Hangup></Hangup>``

Reference: Exotel's official ExoML library (github.com/exotel/goexoml) and the Exotel
developer portal (developer.exotel.com → Programmable Voice → ExoML).

Deliberate differences from the TwiML the previous implementation emitted
------------------------------------------------------------------------
* ``<Gather>`` has **no** ``input``/``speechTimeout``/``model``/``language`` attributes —
  ExoML gather is DTMF only. A ``speech=True`` request therefore renders as DTMF and the
  IVR keeps its keypad path as the supported input (nothing is faked).
* ``<Dial>`` has **no** ``statusCallback``/``statusCallbackEvent`` — the bridged-leg outcome
  arrives on the ``action`` URL as ``DialCallStatus``.
* ``<Dial record>`` is a boolean, not ``record-from-answer``.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin
from xml.sax.saxutils import escape, quoteattr

from fastapi import Request

from backend.config import settings
from backend.services.telephony.markup import (RENDERERS, Dial, Gather, Hangup, Redirect,
                                               Say, VoiceDoc, register_renderer)

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
EXOML_EMPTY = f"{XML_DECLARATION}\n<Response></Response>\n"

# Language codes accepted by ExoML <Say language="…">. Exotel TTS coverage differs from
# Twilio's, so unknown codes fall back to English rather than emitting an invalid tag;
# the caller's chosen language is still stored on CallSession/IVRSurvey.
_EXOML_SAY_LANGUAGES = {"en", "hi", "mr", "te", "kn", "ta", "gu", "bn"}


def _say_language(language: Optional[str]) -> Optional[str]:
    lang = (language or "").lower().strip()
    if not lang:
        return None
    return lang if lang in _EXOML_SAY_LANGUAGES else "en"


def _say_xml(node: Say, indent: str) -> str:
    attrs = ""
    lang = _say_language(node.language)
    if lang:
        attrs += f" language={quoteattr(lang)}"
    if node.loop and node.loop > 1:
        attrs += f' loop="{int(node.loop)}"'
    return f"{indent}<Say{attrs}>{escape(node.text)}</Say>"


def _attr(name: str, value) -> str:
    return "" if value in (None, "") else f" {name}={quoteattr(str(value))}"


def _gather_xml(node: Gather, indent: str) -> str:
    attrs = _attr("action", node.action) + _attr("method", node.method)
    if node.timeout:
        attrs += f' timeout="{int(node.timeout)}"'
    # finishOnKey="" (empty) means "no finish key" in ExoML — omit it to use the default '#'.
    if node.finish_on_key:
        attrs += _attr("finishOnKey", node.finish_on_key)
    if node.num_digits and node.num_digits > 0:
        attrs += f' numDigits="{int(node.num_digits)}"'
    inner = _say_xml(Say(text=node.prompt, language=node.language), indent + "    ")
    return f"{indent}<Gather{attrs}>\n{inner}\n{indent}</Gather>"


def _dial_xml(node: Dial, indent: str) -> str:
    attrs = _attr("action", node.action) + _attr("method", node.method)
    if node.timeout:
        attrs += f' timeout="{int(node.timeout)}"'
    caller_id = node.caller_id or settings.EXOTEL_PHONE_NUMBER
    attrs += _attr("callerId", caller_id)
    if node.record:
        attrs += ' record="true"'
    return f"{indent}<Dial{attrs}>\n{indent}    <Number>{escape(node.number)}</Number>\n{indent}</Dial>"


def _redirect_xml(node: Redirect, indent: str) -> str:
    # ExoML <Redirect> carries the URL as element text (unlike TwiML's url="" attribute).
    return f"{indent}<Redirect{_attr('method', node.method)}>{escape(node.url)}</Redirect>"


def render_exoml(doc: VoiceDoc) -> str:
    """Render a provider-neutral VoiceDoc as an ExoML document."""
    parts = [XML_DECLARATION, "<Response>"]
    for node in doc.nodes:
        if isinstance(node, Say):
            parts.append(_say_xml(node, "    "))
        elif isinstance(node, Gather):
            parts.append(_gather_xml(node, "    "))
        elif isinstance(node, Dial):
            parts.append(_dial_xml(node, "    "))
        elif isinstance(node, Redirect):
            parts.append(_redirect_xml(node, "    "))
        elif isinstance(node, Hangup):
            parts.append("    <Hangup></Hangup>")
        else:  # pragma: no cover - defensive: unknown instruction must not silently vanish
            raise ValueError(f"cannot render {type(node).__name__} as ExoML")
    parts.append("</Response>")
    return "\n".join(parts) + "\n"


register_renderer("exoml", render_exoml)


# ------------------------------------------------------------------------------------------
# URL helpers (ExoML action URLs must be absolute and publicly reachable)
# ------------------------------------------------------------------------------------------
def public_base_url(request: Optional[Request] = None) -> str:
    """Public HTTPS origin Exotel reaches. PUBLIC_API_BASE_URL wins because the reverse
    proxy's Host header may be internal (and in production HTTPS is terminated upstream)."""
    if settings.PUBLIC_API_BASE_URL:
        return settings.PUBLIC_API_BASE_URL.rstrip("/")
    if request is not None:
        return str(request.base_url).rstrip("/")
    return ""


def action_url(request: Optional[Request], path: str, query: str = "") -> str:
    """Absolute URL for an ExoML ``action``/``Redirect`` target.

    The shared webhook secret is appended as a query parameter: Exotel does not sign
    ExoML/StatusCallback webhooks, so the secret in the URL we hand to Exotel is what
    proves the request came from our configured ExoML application (see EXOTEL_SETUP.md).
    """
    from backend.services.telephony.webhook_service import webhook_token_query

    base = public_base_url(request)
    url = urljoin(base + "/", path.lstrip("/"))
    parts = [p for p in (query, webhook_token_query()) if p]
    return f"{url}?{'&'.join(parts)}" if parts else url


__all__ = ["RENDERERS", "render_exoml", "action_url", "public_base_url", "EXOML_EMPTY"]
