"""Store restaurant phone and website from the provider.

Revision ID: 0005_restaurant_contact
Revises: 0004_restaurant_embeddings
Create Date: 2026-10-04

Adds two nullable columns. Existing rows keep NULL until a later search for the
same place fills them. Downgrade drops only these columns.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_restaurant_contact"
down_revision: Union[str, Sequence[str], None] = "0004_restaurant_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not _column_exists("phone"):
        op.add_column("restaurants", sa.Column("phone", sa.String(length=40), nullable=True))
    if not _column_exists("website"):
        op.add_column("restaurants", sa.Column("website", sa.String(length=512), nullable=True))


def downgrade() -> None:
    if _column_exists("website"):
        op.drop_column("restaurants", "website")
    if _column_exists("phone"):
        op.drop_column("restaurants", "phone")


def _column_exists(column: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text("PRAGMA table_info(restaurants)")).all()
        return any(row[1] == column for row in rows)
    count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'restaurants' "
            "AND column_name = :column"
        ),
        {"column": column},
    ).scalar()
    return bool(count)
