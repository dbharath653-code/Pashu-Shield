"""
Deterministic, explainable, versioned rule-based triage.

Temperature handling (section 14)
---------------------------------
* Canonical storage unit: degrees Celsius.
* Callers should send `temperature_unit` ("C" or "F"). When it is omitted the legacy
  behaviour is preserved with an explicit, documented inference: values >= 50 are treated as
  Fahrenheit (no livestock species has a body temperature >= 50 °C) and values < 50 as Celsius.
  The inference is recorded in the triage explanation.
* After conversion the value must lie in PLAUSIBLE_RANGE_C, otherwise it is rejected (422).
* Species fever thresholds below are decision-support defaults, expressed only in °C. They are
  NOT diagnostic criteria and should be reviewed by the state veterinary authority before use
  in production (they live in one table to make that review simple).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

RULESET_VERSION = "2026.09.1"

PLAUSIBLE_RANGE_C = (30.0, 46.0)

# species -> (fever_c, high_fever_c)
FEVER_THRESHOLDS_C: Dict[str, Tuple[float, float]] = {
    "cattle": (39.5, 40.5),
    "buffalo": (39.5, 40.5),
    "sheep": (40.0, 41.0),
    "goat": (40.0, 41.0),
    "pig": (40.0, 41.0),
    "horse": (38.6, 39.5),
    "poultry": (43.0, 44.0),
}
DEFAULT_FEVER_C = (39.5, 40.5)


class TemperatureError(ValueError):
    pass


def fahrenheit_to_celsius(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def normalize_temperature(value: Optional[float], unit: Optional[str]) -> Tuple[Optional[float], Optional[str], bool]:
    """Returns (celsius, unit_used, inferred). Raises TemperatureError for impossible values."""
    if value is None:
        return None, None, False
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise TemperatureError("Temperature must be numeric")
    if value != value or value in (float("inf"), float("-inf")):
        raise TemperatureError("Temperature must be a finite number")
    inferred = False
    u = (unit or "").strip().upper()[:1]
    if u not in ("C", "F"):
        u = "F" if value >= 50.0 else "C"
        inferred = True
    celsius = fahrenheit_to_celsius(value) if u == "F" else value
    celsius = round(celsius, 2)
    lo, hi = PLAUSIBLE_RANGE_C
    if not (lo <= celsius <= hi):
        raise TemperatureError(f"Temperature {value}°{u} ({celsius}°C) is outside the physiologically plausible range {lo}–{hi}°C")
    return celsius, u, inferred


def _species_key(species: str) -> str:
    s = (species or "").strip().lower()
    for key in FEVER_THRESHOLDS_C:
        if key in s:
            return key
    if s in {"cow", "bull", "ox"}:
        return "cattle"
    if s in {"chicken", "hen", "duck", "bird"}:
        return "poultry"
    return s


# ---------------------------------------------------------------------------------------
@dataclass
class TriageContext:
    species: str
    symptoms: List[str]
    number_affected: int
    number_dead: int
    temperature_c: Optional[float]

    def has_symptom(self, *needles: str) -> Optional[str]:
        for s in self.symptoms:
            for n in needles:
                if n in s:
                    return s
        return None


@dataclass
class TriageRule:
    id: str
    level: str  # LOW | MODERATE | HIGH | CRITICAL
    weight: float  # contribution to confidence
    requires_vet: bool
    requires_lab: bool
    test: Callable[[TriageContext], Optional[str]]  # returns an explanation string when triggered


@dataclass
class TriageExplanation:
    rule_id: str
    level: str
    reason: str


@dataclass
class TriageResult:
    risk_level: str
    urgency: str
    confidence: float
    reasons: List[TriageExplanation] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    biosecurity_instructions: List[str] = field(default_factory=list)
    requires_vet: bool = False
    requires_lab: bool = False
    diagnostic_note: str = ""
    temperature_c: Optional[float] = None
    temperature_unit_reported: Optional[str] = None


CRITICAL_SIGNS = ("sudden death", "bleeding from orifices", "paralysis", "severe blisters", "respiratory distress", "rapid death", "severe lameness", "convulsion")
HIGH_CONCERN = ("skin lesions", "nodules", "mouth ulcers", "blisters", "abortion", "swollen lymph nodes", "salivation", "drooling", "lesion", "ulcer")
LAB_SIGNS = ("blister", "lesion", "ulcer", "nodule", "abortion", "bleeding", "sudden death")


def _fever(ctx: TriageContext) -> Tuple[float, float]:
    return FEVER_THRESHOLDS_C.get(_species_key(ctx.species), DEFAULT_FEVER_C)


RULES: List[TriageRule] = [
    TriageRule("MORTALITY", "CRITICAL", 0.35, True, True,
               lambda c: f"{c.number_dead} animal death(s) reported" if c.number_dead > 0 else None),
    TriageRule("CRITICAL_SIGN", "CRITICAL", 0.30, True, True,
               lambda c: (lambda s: f"Critical warning sign reported: '{s}'" if s else None)(c.has_symptom(*CRITICAL_SIGNS))),
    TriageRule("HIGH_FEVER", "HIGH", 0.20, True, False,
               lambda c: f"Temperature {c.temperature_c}°C ≥ high-fever threshold {_fever(c)[1]}°C for {c.species}" if c.temperature_c is not None and c.temperature_c >= _fever(c)[1] else None),
    TriageRule("CLUSTER", "HIGH", 0.20, True, False,
               lambda c: f"{c.number_affected} animals affected (≥3 suggests transmissible disease)" if c.number_affected >= 3 else None),
    TriageRule("HIGH_CONCERN_SIGN", "HIGH", 0.20, True, False,
               lambda c: (lambda s: f"Notifiable-disease-compatible sign reported: '{s}'" if s else None)(c.has_symptom(*HIGH_CONCERN))),
    TriageRule("FEVER", "MODERATE", 0.10, True, False,
               lambda c: f"Temperature {c.temperature_c}°C ≥ fever threshold {_fever(c)[0]}°C for {c.species}" if c.temperature_c is not None and c.temperature_c >= _fever(c)[0] else None),
    TriageRule("ANY_SYMPTOM", "MODERATE", 0.10, True, False,
               lambda c: f"{len(c.symptoms)} symptom(s) reported" if c.symptoms else None),
]

_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
_URGENCY = {"LOW": "ROUTINE", "MODERATE": "ROUTINE", "HIGH": "URGENT", "CRITICAL": "EMERGENCY"}

_ACTIONS = {
    "CRITICAL": [
        "Immediately isolate affected and in-contact animals in a separate shed.",
        "Prevent movement of animals, vehicles, and personnel off premises.",
        "Do NOT dispose of carcasses without veterinary supervision.",
        "A veterinary dispatch request has been raised; call Helpline 1962 if nobody responds.",
    ],
    "HIGH": [
        "Separate symptomatic animals from healthy herd members.",
        "Provide clean shade, fresh water, and soft palatable feed.",
        "Record morning and evening temperatures of the herd.",
        "Avoid unprescribed antibiotics; await veterinary assessment.",
    ],
    "MODERATE": [
        "Maintain clean bedding and good shed ventilation.",
        "Ensure clean drinking water; electrolytes if needed.",
        "Consult the block veterinary officer if signs persist > 24 hours.",
    ],
    "LOW": [
        "Continue standard feeding, biosecurity, and deworming schedule.",
        "Keep booster vaccinations (FMD, HS, BQ, LSD) up to date.",
    ],
}
_BIOSECURITY = {
    "CRITICAL": ["Disinfect footwear (4% sodium carbonate or bleach) at entry/exit.", "Wear boots and gloves when handling suspected livestock.", "Quarantine water troughs and fodder."],
    "HIGH": ["Limit farm visitors and contact with neighbouring herds.", "Disinfect equipment after contact with sick livestock."],
    "MODERATE": ["Maintain standard biosecurity and check vaccination records."],
    "LOW": ["Keep shed dry and vector-free."],
}
_NOTES = {
    "CRITICAL": "Potential high-consequence disease signal. Immediate containment and veterinary investigation warranted.",
    "HIGH": "Presentation indicates significant infectious risk. Requires timely veterinary assessment.",
    "MODERATE": "Mild to moderate signs. Monitor closely for progression.",
    "LOW": "No acute disease signs reported.",
}

DISCLAIMER = (
    "IMPORTANT NOTICE: Pashu-Shield automated triage is an early-warning decision support tool, "
    "not a veterinary diagnosis. Diagnosis and treatment must come from a registered veterinary practitioner."
)


class TriageEngine:
    ruleset_version = RULESET_VERSION

    @classmethod
    def run(cls, species: str, symptoms: List[str], number_affected: int = 1, number_dead: int = 0,
            temperature: Optional[float] = None, temperature_unit: Optional[str] = None) -> TriageResult:
        temp_c, unit, inferred = normalize_temperature(temperature, temperature_unit)
        ctx = TriageContext(
            species=species or "",
            symptoms=[s.lower().strip() for s in (symptoms or []) if s and s.strip()],
            number_affected=max(0, int(number_affected or 0)),
            number_dead=max(0, int(number_dead or 0)),
            temperature_c=temp_c,
        )
        fired: List[Tuple[TriageRule, str]] = [(r, msg) for r in RULES if (msg := r.test(ctx))]
        level = max((r.level for r, _ in fired), key=lambda lv: _ORDER[lv], default="LOW")
        # Confidence reflects how much independent evidence supports the level, not diagnostic accuracy.
        supporting = [r for r, _ in fired if r.level == level]
        confidence = 0.9 if not fired else min(0.95, 0.5 + sum(r.weight for r in supporting))
        reasons = [TriageExplanation(r.id, r.level, msg) for r, msg in fired]
        if inferred:
            reasons.append(TriageExplanation("TEMP_UNIT_INFERRED", "INFO", f"Temperature unit not supplied; interpreted {temperature} as °{unit} (documented rule: ≥50 ⇒ °F)."))
        requires_lab = any(r.requires_lab for r, _ in fired) or bool(ctx.has_symptom(*LAB_SIGNS))
        return TriageResult(
            risk_level=level,
            urgency=_URGENCY[level],
            confidence=round(confidence, 2),
            reasons=reasons,
            recommended_actions=list(_ACTIONS[level]),
            biosecurity_instructions=list(_BIOSECURITY[level]),
            requires_vet=level != "LOW",
            requires_lab=requires_lab and level in ("HIGH", "CRITICAL"),
            diagnostic_note=_NOTES[level],
            temperature_c=temp_c,
            temperature_unit_reported=unit,
        )

    @classmethod
    def evaluate(cls, species: str, symptoms: List[str], number_affected: int = 1, number_dead: int = 0,
                 temperature: Optional[float] = None, district: Optional[str] = None, temperature_unit: Optional[str] = None) -> Dict[str, Any]:
        """Dict form used by the API. Keeps every legacy key for existing consumers."""
        r = cls.run(species, symptoms, number_affected, number_dead, temperature, temperature_unit)
        return {
            "risk_level": r.risk_level,
            "confidence": r.confidence,
            "reasons": [e.reason for e in r.reasons],
            "explanation": [e.__dict__ for e in r.reasons],
            "recommended_actions": r.recommended_actions,
            "requires_vet": r.requires_vet,
            "requires_lab": r.requires_lab,
            "rule_version": RULESET_VERSION,
            "temperature_c": r.temperature_c,
            "temperature_unit_reported": r.temperature_unit_reported,
            "is_diagnosis": False,
            # legacy keys
            "urgency": r.urgency,
            "requires_veterinary_dispatch": r.requires_vet,
            "requires_lab_sampling": r.requires_lab,
            "diagnostic_note": r.diagnostic_note,
            "recommendations": r.recommended_actions,
            "biosecurity_instructions": r.biosecurity_instructions,
            "disclaimer": DISCLAIMER,
            "evaluated_symptoms": symptoms,
        }
