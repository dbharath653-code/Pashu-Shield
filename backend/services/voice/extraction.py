"""Rule-based structured extraction from a call transcript.

Extracts ONLY information actually present in the text. Every field that was not said
stays None — nothing is ever guessed or fabricated, and no disease diagnosis is produced
(this is decision support for the veterinarian, not a diagnosis engine).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

SPECIES_KEYWORDS = {
    "cattle": "Cattle", "cow": "Cattle", "bull": "Cattle",
    "buffalo": "Buffalo",
    "goat": "Goat",
    "sheep": "Sheep",
    "poultry": "Poultry", "chicken": "Poultry", "hen": "Poultry", "duck": "Poultry",
    "pig": "Pig", "horse": "Horse",
}

SYMPTOM_KEYWORDS = [
    ("fever", "Fever"), ("temperature", "Fever"),
    ("not eating", "Loss of appetite"), ("appetite", "Loss of appetite"), ("reduced feeding", "Loss of appetite"),
    ("blister", "Blisters"), ("lesion", "Skin lesions"), ("nodule", "Skin lesions"), ("lump", "Skin lesions"),
    ("lameness", "Lameness"), ("lame", "Lameness"),
    ("salivation", "Excessive salivation"), ("drooling", "Excessive salivation"),
    ("cough", "Cough"), ("discharge", "Nasal discharge"), ("swelling", "Swelling"),
    ("diarrhoea", "Diarrhoea"), ("diarrhea", "Diarrhoea"), ("abortion", "Abortion"),
    ("breathing", "Respiratory distress"), ("cannot stand", "Paralysis"),
]

FIELD_PATTERNS = {
    "affected_count": re.compile(r"(\d+)\s*(?:animals?|cows?|cattle|goats?|sheep|buffalo|birds|head)"),
    "deaths": re.compile(r"(\d+)\s*(?:dead|died|deaths?|died today)"),
    "temperature": re.compile(r"(\d{2}(?:\.\d)?)\s*(?:degree|deg|°)\s*([cfCF])?"),
    "age": re.compile(r"(\d+(?:\.\d)?)\s*(?:year|yr|month|mo)s?\s*old"),
    "sex": re.compile(r"\b(male|female|cow|bullock|heifer|calf)\b", re.I),
    "duration": re.compile(r"(?:since|for|last(?:ed)?)\s*(\d+|one|two|three|four|five|six|seven|week|day)s?\s*(day|week)?", re.I),
}

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10}


def _empty_fields() -> Dict[str, Any]:
    return {
        "species": None,
        "affected_count": None,
        "age": None,
        "sex": None,
        "symptoms": None,             # list, or None when nothing was said
        "symptom_duration": None,
        "temperature": None,          # {"value": float, "unit": "C"|"F"} when actually said
        "deaths": None,
        "vaccination_status": None,   # True/False/None (unknown)
        "location": None,
        "possible_exposure": None,
        "farmer_observations": None,
        "vet_observations": None,
    }


def extract_fields(text: Optional[str]) -> Dict[str, Any]:
    fields = _empty_fields()
    if not text or not text.strip():
        return fields
    low = text.lower()

    for needle, species in SPECIES_KEYWORDS.items():
        if re.search(rf"\b{re.escape(needle)}\b", low):
            fields["species"] = species
            break

    found: List[str] = []
    for needle, label in SYMPTOM_KEYWORDS:
        if needle in low and label not in found:
            found.append(label)
    if found:
        fields["symptoms"] = found

    m = FIELD_PATTERNS["affected_count"].search(text)
    if m:
        fields["affected_count"] = int(m.group(1))

    # deaths: prefer explicit "N dead/died" (already excluded from affected by wording)
    m = re.search(r"(\d+)\s*(?:dead|died|deaths?)", low)
    if m:
        fields["deaths"] = int(m.group(1))
    elif re.search(r"\b(?:no|zero|none)\s*(?:dead|died|deaths?)", low):
        fields["deaths"] = 0

    m = FIELD_PATTERNS["temperature"].search(text)
    if m:
        unit = (m.group(2) or "").upper() or None
        try:
            fields["temperature"] = {"value": float(m.group(1)), "unit": unit}
        except ValueError:
            pass

    m = FIELD_PATTERNS["age"].search(text)
    if m:
        try:
            fields["age"] = float(m.group(1))
        except ValueError:
            pass

    m = FIELD_PATTERNS["sex"].search(low)
    if m:
        fields["sex"] = m.group(1).capitalize()

    m = FIELD_PATTERNS["duration"].search(low)
    if m:
        num_raw = m.group(1)
        n = NUMBER_WORDS.get(num_raw)
        if n is None:
            try:
                n = int(num_raw)
            except ValueError:
                n = None
        unit = (m.group(2) or ("day" if "day" in low else "week"))
        if n:
            fields["symptom_duration"] = f"{n} {unit}{'s' if n != 1 else ''}"

    if re.search(r"\bvaccin", low):
        if re.search(r"\b(?:not|un)\s*vaccin|\bno\s+vaccin", low):
            fields["vaccination_status"] = False
        else:
            fields["vaccination_status"] = True

    if re.search(r"\bvillage\s+([A-Za-z\u0900-\u0D7F][A-Za-z\u0900-\u0D7F\s]{1,60})", text, re.I):
        fields["location"] = re.search(r"\bvillage\s+([A-Za-z\u0900-\u0D7F][A-Za-z\u0900-\u0D7F\s]{1,60})",
                                       text, re.I).group(1).strip().rstrip(".,;:")

    if re.search(r"neighbour|neighbor|new (?:animal|cattle|goat)|market|fair|bought", low):
        fields["possible_exposure"] = True
    elif re.search(r"no\s+(?:contact|exposure)", low):
        fields["possible_exposure"] = False

    # Speaker-tagged observations: lines the vet said after markers like "vet:" are handled
    # by the caller passing only the relevant segment; here we split simple "Farmer:"/"Vet:" labels.
    farmer_lines, vet_lines = [], []
    for line in text.splitlines():
        ln = line.strip()
        if re.match(r"^(farmer|caller|शेतकरी)\s*:", ln, re.I):
            farmer_lines.append(re.sub(r"^([^:]+):\s*", "", ln))
        elif re.match(r"^(vet|veterinarian|doctor|पशुवैद्य)\s*:", ln, re.I):
            vet_lines.append(re.sub(r"^([^:]+):\s*", "", ln))
    if farmer_lines:
        fields["farmer_observations"] = " ".join(farmer_lines)[:2000]
    if vet_lines:
        fields["vet_observations"] = " ".join(vet_lines)[:2000]

    return fields
