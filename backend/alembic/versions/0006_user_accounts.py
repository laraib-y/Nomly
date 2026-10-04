"""User accounts, signed-in browsers, and dinner ownership.

Revision ID: 0006_user_accounts
Revises: 0005_restaurant_contact
Create Date: 2026-10-04

Adds users and auth_sessions, plus a nullable sessions.user_id. Existing dinners
keep user_id NULL and behave exactly like guest dinners. Restaurant data is not
touched. Downgrade removes only what this revision added.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_user_accounts"
down_revision: Union[str, Sequence[str], None] = "0005_restaurant_contact"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("display_name", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _table_exists("auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
        op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)

    if not _column_exists("sessions", "user_id"):
        with op.batch_alter_table("sessions") as batch:
            batch.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
            batch.create_index("ix_sessions_user_id", ["user_id"], unique=False)
            batch.create_foreign_key("fk_sessions_user_id", "users", ["user_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    if _column_exists("sessions", "user_id"):
        with op.batch_alter_table("sessions") as batch:
            batch.drop_constraint("fk_sessions_user_id", type_="foreignkey")
            batch.drop_index("ix_sessions_user_id")
            batch.drop_column("user_id")
    if _table_exists("auth_sessions"):
        op.drop_table("auth_sessions")
    if _table_exists("users"):
        op.drop_table("users")


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _column_exists(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return any(item["name"] == column for item in inspector.get_columns(table))
