"""Store dinner intent and fair-matching preferences.

Revision ID: 0003_fair_preferences
Revises: 0002_restaurant_categories
Create Date: 2026-10-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_fair_preferences"
down_revision: Union[str, Sequence[str], None] = "0002_restaurant_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("intent_json", sa.Text(), nullable=True))
    op.drop_constraint("ck_swipes_decision", "swipes", type_="check")
    op.alter_column("swipes", "decision", existing_type=sa.String(length=8), type_=sa.String(length=16), existing_nullable=False)
    op.add_column("swipes", sa.Column("quota_key", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE swipes SET quota_key = CONCAT('standard:', restaurant_id) WHERE quota_key IS NULL"
    )
    op.alter_column("swipes", "quota_key", existing_type=sa.String(length=64), nullable=False)
    op.create_check_constraint(
        "ck_swipes_decision",
        "swipes",
        "decision IN ('like', 'pass', 'super_like', 'veto')",
    )
    op.create_unique_constraint(
        "uq_swipes_participant_quota",
        "swipes",
        ["session_id", "participant_id", "quota_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_swipes_participant_quota", "swipes", type_="unique")
    op.drop_constraint("ck_swipes_decision", "swipes", type_="check")
    op.drop_column("swipes", "quota_key")
    op.alter_column("swipes", "decision", existing_type=sa.String(length=16), type_=sa.String(length=8), existing_nullable=False)
    op.create_check_constraint("ck_swipes_decision", "swipes", "decision IN ('like', 'pass')")
    op.drop_column("sessions", "intent_json")
