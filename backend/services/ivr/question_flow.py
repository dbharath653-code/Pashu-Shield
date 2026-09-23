"""DTMF question definitions for the IVR survey: order, options, validation, normalisation.

Rules (per spec §14):
  * DTMF first (speech is a secondary mechanism on the location question),
  * every answer is validated; invalid input re-asks the question (max 3 attempts),
  * normalised values are stored; unknown stays unknown (None) — nothing is ever fabricated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

QUESTION_ORDER: Tuple[str, ...] = (
    "species", "affected_count", "symptoms", "duration", "deaths", "vaccination", "location", "confirm",
)

MAX_INVALID_ATTEMPTS = 3
MAX_COUNT = 9999

# DTMF -> canonical species (existing DiseaseReport species strings)
SPECIES_OPTIONS: Dict[str, str] = {
    "1": "Cattle", "2": "Buffalo", "3": "Goat", "4": "Sheep", "5": "Poultry", "6": "Other",
}

# Multi-select symptom keys (digits combined before '#', e.g. "13#" -> Fever + Skin lesions)
SYMPTOM_OPTIONS: Dict[str, str] = {
    "1": "Fever",
    "2": "Loss of appetite",
    "3": "Skin lesions",
    "4": "Blisters",
    "5": "Lameness",
    "6": "Excessive salivation",
    "7": "Cough",
    "8": "Nasal discharge",
}
SYMPTOM_UNKNOWN = "9"  # caller cannot say -> symptoms unknown (empty list, never guessed)

DURATION_OPTIONS: Dict[str, Dict[str, Any]] = {
    "1": {"value": "lt_1_day", "label": "Less than a day"},
    "2": {"value": "1_2_days", "label": "1-2 days"},
    "3": {"value": "3_7_days", "label": "3-7 days"},
    "4": {"value": "gt_1_week", "label": "More than a week"},
    "5": {"value": None, "label": "Unknown"},  # explicitly unknown -> null
}

VACCINATION_OPTIONS: Dict[str, Optional[bool]] = {"1": True, "2": False, "3": None}


@dataclass
class Question:
    key: str
    kind: str  # choice | count | multi | speech_location | confirm
    required: bool = True  # whether an unanswered value aborts the survey (species/count/deaths/confirm)
    options: Dict[str, Any] = field(default_factory=dict)
    allow_unknown: bool = False  # safe to store None and move on after repeated invalid input

    # Returns (accepted, normalized_value, raw_input). accepted=False -> re-ask.
    def validate(self, raw: str) -> Tuple[bool, Any, str]:
        raw = (raw or "").strip()
        if self.kind == "choice":
            v = self.options.get(raw)
            if v is None and raw not in self.options:
                return False, None, raw
            # vaccination options legitimately map to None (unknown) for key "3"
            if self.key == "vaccination":
                if raw not in VACCINATION_OPTIONS:
                    return False, None, raw
                return True, VACCINATION_OPTIONS[raw], raw
            return (v is not None), (v if v is not None else None), raw

        if self.kind == "count":
            digits = re.sub(r"\D", "", raw)
            if not digits or not digits.isdigit():
                return False, None, raw
            n = int(digits)
            if n < 0 or n > MAX_COUNT:
                return False, None, raw
            if self.key == "affected_count" and n < 1:
                return False, None, raw  # at least one animal is affected (they called about it)
            return True, n, raw

        if self.kind == "multi":
            digits = [d for d in raw if d.isdigit()]
            if not digits:
                return False, None, raw
            if SYMPTOM_UNKNOWN in digits:
                if len(digits) == 1:
                    return True, None, raw  # unknown -> null (stored as unknown answer)
                return False, None, raw
            chosen: List[str] = []
            for d in digits:
                label = SYMPTOM_OPTIONS.get(d)
                if label is None:
                    return False, None, raw
                if label not in chosen:
                    chosen.append(label)
            return True, chosen, raw

        if self.kind == "speech_location":
            # "1" => registered village (resolved later by the engine); otherwise a spoken name.
            if raw == "1":
                return True, {"registered": True}, raw
            text = re.sub(r"\s+", " ", raw).strip()
            if 1 < len(text) <= 120 and not text.isdigit():
                return True, {"village": text}, raw
            return False, None, raw

        if self.kind == "confirm":
            if raw == "1":
                return True, "CONFIRM", raw
            if raw == "2":
                return True, "RESTART", raw
            if raw == "9":
                return True, "CANCEL", raw
            return False, None, raw

        return False, None, raw


QUESTIONS: Dict[str, Question] = {
    "species": Question("species", "choice", required=True, options=SPECIES_OPTIONS),
    "affected_count": Question("affected_count", "count", required=True),
    "symptoms": Question("symptoms", "multi", required=False, allow_unknown=True),
    "duration": Question("duration", "choice", required=False, allow_unknown=True, options=DURATION_OPTIONS),
    "deaths": Question("deaths", "count", required=True),
    "vaccination": Question("vaccination", "choice", required=False, allow_unknown=True, options=VACCINATION_OPTIONS),
    "location": Question("location", "speech_location", required=False, allow_unknown=True),
    "confirm": Question("confirm", "confirm", required=True),
}


def next_question(current: Optional[str]) -> Optional[str]:
    """Key of the question after `current` (None -> first). Returns None after the last one."""
    if current is None:
        return QUESTION_ORDER[0]
    try:
        idx = QUESTION_ORDER.index(current)
    except ValueError:
        return QUESTION_ORDER[0]
    return QUESTION_ORDER[idx + 1] if idx + 1 < len(QUESTION_ORDER) else None
