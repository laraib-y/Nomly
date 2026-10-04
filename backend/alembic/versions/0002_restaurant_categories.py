"""Add restaurant categories.

Revision ID: 0002_restaurant_categories
Revises: 0001_initial
Create Date: 2026-10-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_restaurant_categories"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("categories", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("restaurants", "categories")
