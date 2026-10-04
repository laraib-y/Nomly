"""Initial DineOff schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_code", sa.String(length=8), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("host_participant_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('lobby', 'active', 'completed')", name="ck_sessions_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_code", name="uq_sessions_room_code"),
    )
    op.create_index("ix_sessions_room_code", "sessions", ["room_code"], unique=False)
    op.create_index("ix_sessions_host_participant_id", "sessions", ["host_participant_id"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)

    op.create_table(
        "participants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("nickname", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "nickname", name="uq_participants_session_nickname"),
    )
    op.create_index("ix_participants_session_id", "participants", ["session_id"], unique=False)

    op.create_table(
        "restaurants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cuisine", sa.String(length=120), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_restaurants_source_external"),
    )
    op.create_index("ix_restaurants_external_id", "restaurants", ["external_id"], unique=False)

    op.create_table(
        "session_restaurants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("restaurant_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "restaurant_id", name="uq_session_restaurants_pair"),
        sa.UniqueConstraint("session_id", "position", name="uq_session_restaurants_position"),
    )
    op.create_index("ix_session_restaurants_session_id", "session_restaurants", ["session_id"], unique=False)
    op.create_index(
        "ix_session_restaurants_restaurant_id",
        "session_restaurants",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "swipes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("participant_id", sa.String(length=36), nullable=False),
        sa.Column("restaurant_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("decision IN ('like', 'pass')", name="ck_swipes_decision"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "participant_id",
            "restaurant_id",
            name="uq_swipes_participant_restaurant",
        ),
    )
    op.create_index("ix_swipes_session_id", "swipes", ["session_id"], unique=False)
    op.create_index("ix_swipes_participant_id", "swipes", ["participant_id"], unique=False)
    op.create_index("ix_swipes_restaurant_id", "swipes", ["restaurant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("swipes")
    op.drop_table("session_restaurants")
    op.drop_table("restaurants")
    op.drop_table("participants")
    op.drop_table("sessions")
