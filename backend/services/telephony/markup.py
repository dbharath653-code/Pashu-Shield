"""Provider-neutral voice markup for the IVR.

The IVR business logic (``services/telephony/webhook_service.py``, ``routers/ivr.py``)
describes what must happen on the call as an ordered sequence of :class:`VoiceDoc`
instructions. A renderer converts that document into the provider's wire format —
Exotel **ExoML** today (``services/telephony/exoml.py``).

Why this module exists
----------------------
Exotel does not use TwiML. Its markup language (ExoML) has a different verb set and
different attributes (``<Gather>`` has no speech input, ``<Dial>`` has no status callback,
``<Redirect>`` carries the URL as element text, ...). Keeping the IVR flow expressed in
provider-neutral instructions is what lets Pashu Shield's business logic stay identical
when the telephony transport changes — the requirement that "Exotel must be a transport
layer, not the business-logic layer".

Adding a provider means adding a renderer and setting ``markup_dialect`` on that provider;
no business-logic file changes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# A spoken prompt is capped: an over-long <Say> makes Exotel hang up mid-menu and the
# caller hears nothing. 1000 characters is far more than any Pashu Shield prompt needs.
MAX_PROMPT_CHARS = 1000
_WHITESPACE = re.compile(r"\s+")


def clean_prompt(text: Optional[str]) -> str:
    """Normalise prompt text for speech synthesis (collapse whitespace, cap length)."""
    if not text:
        return ""
    return _WHITESPACE.sub(" ", str(text)).strip()[:MAX_PROMPT_CHARS]


# ------------------------------------------------------------------------------------------
# Instructions
# ------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Say:
    """Speak text (text-to-speech)."""
    text: str
    language: Optional[str] = None
    loop: int = 1


@dataclass(frozen=True)
class Gather:
    """Play `prompt`, then collect DTMF and POST the result to `action`.

    `speech` records that the flow would accept spoken input; renderers for providers
    without DTMF-plus-speech gather (Exotel ExoML) render DTMF only and never pretend
    otherwise — the IVR always has a working keypad path.
    """
    prompt: str
    action: str
    language: Optional[str] = None
    method: str = "POST"
    timeout: int = 6
    finish_on_key: str = "#"
    num_digits: int = 1
    speech: bool = False


@dataclass(frozen=True)
class Dial:
    """Bridge the caller to `number`; POST the leg outcome to `action`."""
    number: str
    action: str
    method: str = "POST"
    timeout: int = 20
    caller_id: Optional[str] = None
    record: bool = False


@dataclass(frozen=True)
class Redirect:
    """Transfer control of the call to another ExoML document at `url`."""
    url: str
    method: str = "POST"


@dataclass(frozen=True)
class Hangup:
    """End the call."""


VoiceNode = object


@dataclass
class VoiceDoc:
    """An ordered list of voice instructions, rendered by the active provider."""
    nodes: List[VoiceNode] = field(default_factory=list)

    def say(self, text: str, language: Optional[str] = None, loop: int = 1) -> "VoiceDoc":
        cleaned = clean_prompt(text)
        if cleaned:
            self.nodes.append(Say(text=cleaned, language=language, loop=max(1, int(loop or 1))))
        return self

    def gather(self, prompt: str, action: str, *, language: Optional[str] = None, method: str = "POST",
               timeout: int = 6, finish_on_key: str = "#", num_digits: int = 1,
               speech: bool = False) -> "VoiceDoc":
        self.nodes.append(Gather(prompt=clean_prompt(prompt), action=action, language=language,
                                 method=method, timeout=max(1, int(timeout or 1)),
                                 finish_on_key=finish_on_key or "", num_digits=max(0, int(num_digits or 0)),
                                 speech=bool(speech)))
        return self

    def dial(self, number: str, action: str, *, method: str = "POST", timeout: int = 20,
             caller_id: Optional[str] = None, record: bool = False) -> "VoiceDoc":
        self.nodes.append(Dial(number=str(number or "").strip(), action=action, method=method,
                               timeout=max(1, int(timeout or 1)), caller_id=caller_id, record=bool(record)))
        return self

    def redirect(self, url: str, method: str = "POST") -> "VoiceDoc":
        self.nodes.append(Redirect(url=url, method=method))
        return self

    def hangup(self) -> "VoiceDoc":
        self.nodes.append(Hangup())
        return self

    def say_and_hangup(self, text: str, language: Optional[str] = None) -> "VoiceDoc":
        return self.say(text, language=language).hangup()


# ------------------------------------------------------------------------------------------
# Rendering
# ------------------------------------------------------------------------------------------
# markup dialect -> renderer. A provider declares its dialect; the registry is the single
# place a new provider's wire format is wired in.
RENDERERS: Dict[str, Callable[[VoiceDoc], str]] = {}


def register_renderer(dialect: str, renderer: Callable[[VoiceDoc], str]) -> None:
    RENDERERS[dialect] = renderer


def render(doc: VoiceDoc, dialect: str) -> str:
    """Render `doc` to the provider's XML markup. Raises for an unknown dialect rather
    than silently emitting another provider's format."""
    renderer = RENDERERS.get(dialect)
    if renderer is None:
        raise ValueError(f"no voice markup renderer registered for dialect {dialect!r}")
    return renderer(doc)


def voice_response(doc: VoiceDoc) -> "object":
    """FastAPI XML response for `doc`, using the active telephony provider's dialect."""
    from fastapi.responses import Response

    from backend.services.telephony import get_provider

    provider = get_provider()
    return Response(content=render(doc, provider.markup_dialect), media_type="application/xml")


def empty_voice_response() -> "object":
    """Empty document: used by telemetry endpoints that must not alter the live call."""
    return voice_response(VoiceDoc())
