"""Inbound IVR / telephony tables: call_sessions, call_transcripts, ivr_surveys,
ivr_survey_responses, callback_requests.

Revision ID: 0003_telephony_ivr
Revises: 0002_postgis
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_telephony_ivr"
down_revision = "0002_postgis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_call_id", sa.String(length=64), nullable=False),
        sa.Column("caller_phone", sa.String(length=32), nullable=True),
        sa.Column("to_phone", sa.String(length=32), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("district", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("farmer_id", sa.String(length=64), nullable=True),
        sa.Column("veterinarian_id", sa.String(length=64), nullable=True),
        sa.Column("disease_report_id", sa.String(length=64), nullable=True),
        sa.Column("ivr_survey_id", sa.String(length=64), nullable=True),
        sa.Column("recording_status", sa.String(length=32), nullable=False),
        sa.Column("recording_sid", sa.String(length=64), nullable=True),
        sa.Column("recording_url", sa.String(length=512), nullable=True),
        sa.Column("recording_duration", sa.Integer(), nullable=True),
        sa.Column("transcription_status", sa.String(length=32), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("vet_attempts", sa.JSON(), nullable=True),
        sa.Column("last_status", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["farmer_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["veterinarian_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["disease_report_id"], ["disease_reports.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("call_sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_call_sessions_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_provider_call_id"), ["provider_call_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_call_sessions_caller_phone"), ["caller_phone"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_district"), ["district"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_farmer_id"), ["farmer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_veterinarian_id"), ["veterinarian_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_disease_report_id"), ["disease_report_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_ivr_survey_id"), ["ivr_survey_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_started_at"), ["started_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_sessions_created_at"), ["created_at"], unique=False)
        batch_op.create_index("ix_calls_status_started", ["status", "started_at"], unique=False)

    op.create_table(
        "call_transcripts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("call_session_id", sa.String(length=64), nullable=False),
        sa.Column("speaker", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=True),
        sa.Column("end_time", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("call_transcripts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_call_transcripts_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_transcripts_call_session_id"), ["call_session_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_call_transcripts_created_at"), ["created_at"], unique=False)
        batch_op.create_index("ix_transcript_session_start", ["call_session_id", "start_time"], unique=False)

    op.create_table(
        "ivr_surveys",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("call_session_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("current_question", sa.String(length=32), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("disease_report_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["disease_report_id"], ["disease_reports.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ivr_surveys", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ivr_surveys_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ivr_surveys_call_session_id"), ["call_session_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ivr_surveys_created_at"), ["created_at"], unique=False)

    op.create_table(
        "ivr_survey_responses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("survey_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.String(length=32), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("normalized_answer", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["survey_id"], ["ivr_surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("survey_id", "question", name="uq_survey_question"),
    )
    with op.batch_alter_table("ivr_survey_responses", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ivr_survey_responses_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ivr_survey_responses_survey_id"), ["survey_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ivr_survey_responses_created_at"), ["created_at"], unique=False)

    op.create_table(
        "callback_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("farmer_id", sa.String(length=64), nullable=True),
        sa.Column("call_session_id", sa.String(length=64), nullable=True),
        sa.Column("disease_report_id", sa.String(length=64), nullable=True),
        sa.Column("caller_phone", sa.String(length=32), nullable=True),
        sa.Column("district", sa.String(length=128), nullable=True),
        sa.Column("taluka", sa.String(length=128), nullable=True),
        sa.Column("village", sa.String(length=128), nullable=True),
        sa.Column("species", sa.String(length=64), nullable=True),
        sa.Column("symptoms", sa.JSON(), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_veterinarian", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["farmer_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ),
        sa.ForeignKeyConstraint(["disease_report_id"], ["disease_reports.id"], ),
        sa.ForeignKeyConstraint(["assigned_veterinarian"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("callback_requests", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_callback_requests_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_farmer_id"), ["farmer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_call_session_id"), ["call_session_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_disease_report_id"), ["disease_report_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_district"), ["district"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_priority"), ["priority"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_assigned_veterinarian"), ["assigned_veterinarian"], unique=False)
        batch_op.create_index(batch_op.f("ix_callback_requests_created_at"), ["created_at"], unique=False)
        batch_op.create_index("ix_callback_status_priority", ["status", "priority"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("callback_requests", schema=None) as batch_op:
        batch_op.drop_index("ix_callback_status_priority")
        for idx in ("ix_callback_requests_created_at", "ix_callback_requests_assigned_veterinarian",
                    "ix_callback_requests_status", "ix_callback_requests_priority",
                    "ix_callback_requests_district", "ix_callback_requests_disease_report_id",
                    "ix_callback_requests_call_session_id", "ix_callback_requests_farmer_id",
                    "ix_callback_requests_id"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    op.drop_table("callback_requests")

    with op.batch_alter_table("ivr_survey_responses", schema=None) as batch_op:
        for idx in ("ix_ivr_survey_responses_created_at", "ix_ivr_survey_responses_survey_id", "ix_ivr_survey_responses_id"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    op.drop_table("ivr_survey_responses")

    with op.batch_alter_table("ivr_surveys", schema=None) as batch_op:
        for idx in ("ix_ivr_surveys_created_at", "ix_ivr_surveys_call_session_id", "ix_ivr_surveys_id"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    op.drop_table("ivr_surveys")

    with op.batch_alter_table("call_transcripts", schema=None) as batch_op:
        batch_op.drop_index("ix_transcript_session_start")
        for idx in ("ix_call_transcripts_created_at", "ix_call_transcripts_call_session_id", "ix_call_transcripts_id"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    op.drop_table("call_transcripts")

    with op.batch_alter_table("call_sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_calls_status_started")
        for idx in ("ix_call_sessions_created_at", "ix_call_sessions_started_at", "ix_call_sessions_ivr_survey_id",
                    "ix_call_sessions_disease_report_id", "ix_call_sessions_veterinarian_id",
                    "ix_call_sessions_farmer_id", "ix_call_sessions_status",
                    "ix_call_sessions_caller_phone", "ix_call_sessions_provider_call_id", "ix_call_sessions_id"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    op.drop_table("call_sessions")
