"""IVR main-menu definitions.

One place decides what a keypad digit means, so the prompt text (``services/ivr/prompts.py``),
the flow (``services/telephony/webhook_service.py``) and the dashboard cannot drift apart.

    1 — report a sick animal
    2 — request a veterinarian
    3 — check case / report status
    0 — emergency

Pressing 0 records that the *caller* asked for emergency help. It never implies a diagnosis
and never overrides triage: clinical risk is whatever ``TriageEngine`` computes from the
answers the caller actually gives.
"""
from __future__ import annotations

from typing import Dict, Optional

MENU_REPORT = "1"
MENU_VETERINARIAN = "2"
MENU_CASE_STATUS = "3"
MENU_EMERGENCY = "0"

MENU_OPTIONS: Dict[str, str] = {
    MENU_REPORT: "REPORT_DISEASE",
    MENU_VETERINARIAN: "REQUEST_VETERINARIAN",
    MENU_CASE_STATUS: "CASE_STATUS",
    MENU_EMERGENCY: "EMERGENCY",
}

#: How many times the menu may be re-asked before the call is ended politely.
MAX_MENU_ATTEMPTS = 2


def parse_menu_option(digits: str) -> Optional[str]:
    """Return the menu digit when it is a valid option, else ``None``.

    ExoML gathers with ``numDigits=1`` return a single digit; the finish key (``#``/``*``)
    is already stripped by the provider adapter, so anything else is simply invalid input
    and the caller hears the menu again.
    """
    key = (digits or "").strip()
    return key if key in MENU_OPTIONS else None


def option_name(digits: str) -> Optional[str]:
    return MENU_OPTIONS.get((digits or "").strip())
