"""Veterinary-support call summary generation.

Two providers:
  * AI_SUMMARY_PROVIDER unset/none -> deterministic template summary built ONLY from the
    extracted fields (always available, never invents values).
  * AI_SUMMARY_PROVIDER=openai     -> LLM polishing with the same field payload; on any
    failure we fall back to the template. The prompt forbids diagnosing.

The summary explicitly states "Veterinary assessment required" and never claims a disease
unless the veterinarian said it in the conversation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from backend.config import settings

logger = logging.getLogger("pashu_shield.voice")

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

TEMPLATE = """CALL SUMMARY

Species: {species}
Affected: {affected}
Symptoms: {symptoms}
Duration: {duration}
Deaths: {deaths}
Vaccination: {vaccination}
Location: {location}
Temperature: {temperature}

Important observations: {observations}
Suggested next action: Veterinary assessment required.
(Decision support only — not a diagnosis.)"""


def template_summary(fields: Dict[str, Any]) -> str:
    def fmt(v, unknown="Unknown"):
        if v is None or v == "" or v == []:
            return unknown
        if isinstance(v, bool):
            return "Yes" if v else "No"
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return str(v)

    temp = fields.get("temperature")
    if isinstance(temp, dict):
        temp_s = f"{temp.get('value')}°{temp.get('unit') or '?'}"
    else:
        temp_s = "Unknown"

    observations = []
    if fields.get("possible_exposure") is True:
        observations.append("Possible exposure to other animals/market reported")
    if fields.get("farmer_observations"):
        observations.append(f"Farmer: {fields['farmer_observations']}")
    if fields.get("vet_observations"):
        observations.append(f"Veterinarian: {fields['vet_observations']}")
    if not observations:
        observations.append("None recorded")

    return TEMPLATE.format(
        species=fmt(fields.get("species")),
        affected=fmt(fields.get("affected_count")),
        symptoms=fmt(fields.get("symptoms")),
        duration=fmt(fields.get("symptom_duration")),
        deaths=fmt(fields.get("deaths")),
        vaccination=fmt(fields.get("vaccination_status")),
        location=fmt(fields.get("location")),
        temperature=temp_s,
        observations="; ".join(observations),
    )


async def generate_summary(fields: Dict[str, Any], transcript: Optional[str] = None) -> Dict[str, Any]:
    """Returns {"status", "summary", "provider"}."""
    base = template_summary(fields)
    provider = (settings.AI_SUMMARY_PROVIDER or "").lower()
    if provider in ("", "none"):
        return {"status": "OK", "summary": base, "provider": "template"}
    if provider == "openai" and settings.AI_SUMMARY_API_KEY:
        prompt = (
            "You are a veterinary call-centre assistant. Write a concise support summary "
            "using ONLY the extracted fields below. Do NOT diagnose or name a disease. "
            "End with 'Suggested next action: Veterinary assessment required.'\n\n"
            f"Extracted fields: {fields}\n\n"
            f"Transcript excerpt (may be partial): {(transcript or '')[:4000]}"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    OPENAI_CHAT_URL,
                    headers={"Authorization": f"Bearer {settings.AI_SUMMARY_API_KEY}"},
                    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 500, "temperature": 0.2},
                )
            if resp.status_code == 200:
                content = (((resp.json().get("choices") or [{}])[0]).get("message") or {}).get("content")
                if content and content.strip():
                    return {"status": "OK", "summary": content.strip(), "provider": "openai"}
            logger.warning("summary provider error", extra={"fields": {"status": resp.status_code}})
        except httpx.HTTPError as e:
            logger.warning("summary provider failure", extra={"fields": {"error": type(e).__name__}})
    return {"status": "OK", "summary": base, "provider": "template_fallback"}
