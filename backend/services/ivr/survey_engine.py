"""Survey engine: processes one DTMF/speech answer at a time, keeps the IVRSurvey row
in sync, persists validated normalised answers (idempotent per question), and builds the
existing `DiseaseReportCreate` payload from the collected answers when the farmer confirms.

It never fabricates clinical data: missing/unknown values stay None and only fields the
caller actually supplied ( or that come from the caller's own registered profile) are set.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import IVRSurvey, IVRSurveyResponse, User
from backend.schemas import DiseaseReportCreate
from backend.services.ivr import prompts
from backend.services.ivr.question_flow import (MAX_INVALID_ATTEMPTS, QUESTIONS, QUESTION_ORDER,
                                                next_question)

logger = logging.getLogger("pashu_shield.ivr")


class SurveyEngine:
    # ---- lifecycle ------------------------------------------------------------------------
    @staticmethod
    async def start(db: AsyncSession, session, language: str) -> IVRSurvey:
        """Create (or return the existing) survey for a call session — duplicate webhooks
        must not create a second survey."""
        existing = (await db.execute(select(IVRSurvey).where(IVRSurvey.call_session_id == session.id))).scalars().first()
        if existing:
            return existing
        survey = IVRSurvey(
            id=f"IVR-{uuid.uuid4().hex[:10].upper()}",
            call_session_id=session.id,
            status="IN_PROGRESS",
            language=language or "en",
            current_question=QUESTION_ORDER[0],
            attempts=0,
        )
        db.add(survey)
        await db.flush()
        session.ivr_survey_id = survey.id
        return survey

    # ---- prompts -----------------------------------------------------------------------------
    @staticmethod
    def question_prompt(language: str, question_key: str) -> str:
        return prompts.prompt(language, question_key)

    @staticmethod
    def intro_prompt(language: str) -> str:
        return prompts.prompt(language, "greeting")

    # ---- answer processing --------------------------------------------------------------------
    @staticmethod
    async def record_answer(db: AsyncSession, survey: IVRSurvey, question_key: str,
                            raw_input: str, normalized: Any) -> Optional[IVRSurveyResponse]:
        """Persist one answer. Unique (survey_id, question) => duplicate webhook replays
        do not create duplicate rows (the existing row is returned untouched)."""
        existing = (await db.execute(select(IVRSurveyResponse).where(
            IVRSurveyResponse.survey_id == survey.id, IVRSurveyResponse.question == question_key
        ))).scalars().first()
        if existing:
            return existing
        row = IVRSurveyResponse(
            id=f"IVRS-{uuid.uuid4().hex[:10].upper()}",
            survey_id=survey.id,
            question=question_key,
            answer=(raw_input or "")[:2000],
            normalized_answer=_jsonable(normalized),
            created_at=datetime.utcnow(),
        )
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def answers(db: AsyncSession, survey: IVRSurvey) -> Dict[str, Any]:
        rows = (await db.execute(select(IVRSurveyResponse).where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
        return {r.question: r.normalized_answer for r in rows}

    @staticmethod
    def handle_input(survey: IVRSurvey, raw_input: str, valid: bool) -> str:
        """Advance the survey cursor. Returns one of: 'ok' | 'invalid' | 'exhausted'."""
        if valid:
            nxt = next_question(survey.current_question)
            survey.attempts = 0
            survey.current_question = nxt or "done"
            return "ok"
        survey.attempts = (survey.attempts or 0) + 1
        if survey.attempts >= MAX_INVALID_ATTEMPTS:
            # Store unknown/null for optional questions; abort handled by caller for required ones.
            q = QUESTIONS.get(survey.current_question or "")
            if q is not None and q.required and not q.allow_unknown:
                return "exhausted"
            nxt = next_question(survey.current_question)
            survey.attempts = 0
            survey.current_question = nxt or "done"
            return "exhausted"
        return "invalid"

    @staticmethod
    def restart(survey: IVRSurvey) -> None:
        survey.current_question = QUESTION_ORDER[0]
        survey.attempts = 0

    # ---- report payload ---------------------------------------------------------------------------
    @staticmethod
    async def build_report_create(db: AsyncSession, session, survey: IVRSurvey) -> DiseaseReportCreate:
        """Translate confirmed survey answers into the EXISTING DiseaseReportCreate schema
        so the normal report pipeline (triage -> case -> dispatch -> alert) runs unchanged."""
        answers = await SurveyEngine.answers(db, survey)

        species = answers.get("species")
        if not isinstance(species, str) or not species.strip():
            raise ValueError("species_missing")

        number_affected = answers.get("affected_count")
        if not isinstance(number_affected, int) or number_affected < 1:
            raise ValueError("affected_count_missing")

        number_dead = answers.get("deaths")
        if not isinstance(number_dead, int) or number_dead < 0:
            raise ValueError("deaths_missing")

        symptoms_raw = answers.get("symptoms")
        symptoms: List[str] = list(symptoms_raw) if isinstance(symptoms_raw, list) else []

        duration = answers.get("duration")
        duration_label = duration.get("label") if isinstance(duration, dict) else None

        vaccination = answers.get("vaccination")  # True | False | None (unknown)
        location = answers.get("location") if isinstance(answers.get("location"), dict) else {}

        village, district, taluka = await _resolve_location(db, session, location)

        notes_parts = [f"IVR call {session.id} (survey {survey.id})"]
        if duration_label:
            notes_parts.append(f"Symptom duration: {duration_label}")
        else:
            notes_parts.append("Symptom duration: Unknown")
        if vaccination is True:
            notes_parts.append("Vaccination status: Vaccinated")
        elif vaccination is False:
            notes_parts.append("Vaccination status: Not vaccinated")
        else:
            notes_parts.append("Vaccination status: Unknown")
        if answers.get("location") is None:
            notes_parts.append("Location: not provided by caller")
        notes = "; ".join(p for p in notes_parts if p)[:4000]

        return DiseaseReportCreate(
            species=species,
            number_affected=number_affected,
            number_dead=number_dead,
            symptoms=symptoms,
            temperature=None,            # never invented from IVR data
            temperature_unit=None,
            district=district,
            taluka=taluka,
            village=village,
            suspected_disease="Unknown",  # no diagnosis is ever guessed from a phone survey
            notes=notes,
        )


async def _resolve_location(db: AsyncSession, session, location: Dict[str, Any]):
    """Village/district resolution order: caller's registered profile (their own statement
    via 'press 1') -> spoken village name (district Unknown unless registered) -> unknown."""
    farmer: Optional[User] = None
    if session.farmer_id:
        farmer = await db.get(User, session.farmer_id)
    if location.get("registered") and farmer is not None:
        return (farmer.village or "Unknown"), farmer.district or "Unknown", farmer.taluka
    spoken = location.get("village")
    if spoken:
        if farmer is not None and farmer.village:
            return spoken, farmer.district or "Unknown", farmer.taluka
        return spoken, "Unknown", None
    if farmer is not None and farmer.village:
        return farmer.village, farmer.district or "Unknown", farmer.taluka
    return "Unknown", "Unknown", None


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    return str(v)
