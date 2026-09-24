"""IVR main menu + emergency flag on call_sessions.

Adds the two fields the Exotel IVR main menu needs and nothing else:

  * ``ivr_menu_option`` – which menu entry the caller chose (1 report, 2 veterinarian,
    3 case status, 0 emergency). Species / counts / symptoms / location already live in
    ``ivr_survey_responses`` and the created report id in ``disease_reports``, so no
    duplicate storage is introduced.
  * ``is_emergency``    – the caller pressed 0. This records *what the caller asked for*;
    clinical risk stays whatever the existing triage engine computed, and no disease is
    ever inferred from the keypress.

Both columns are nullable / defaulted, so existing rows keep working and the change is
reversible without data loss.

Revision ID: 0004_ivr_menu
Revises: 0003_telephony_ivr
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_ivr_menu"
down_revision = "0003_telephony_ivr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("call_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ivr_menu_option", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("is_emergency", sa.Boolean(), nullable=False,
                                      server_default=sa.false()))
    # The server default exists only so existing rows backfill; drop it so the schema
    # matches the model (which defaults in Python).
    with op.batch_alter_table("call_sessions", schema=None) as batch_op:
        batch_op.alter_column("is_emergency", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("call_sessions", schema=None) as batch_op:
        batch_op.drop_column("is_emergency")
        batch_op.drop_column("ivr_menu_option")
