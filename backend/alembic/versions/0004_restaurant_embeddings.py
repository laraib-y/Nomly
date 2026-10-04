"""Store grounded restaurant text and embeddings.

Revision ID: 0004_restaurant_embeddings
Revises: 0003_fair_preferences
Create Date: 2026-10-04

Adds nullable semantic text, its hash, and a portable embedding JSON column.
On TiDB, also adds a VECTOR column of the same dimension. Downgrade drops
only those columns. Sessions, swipes, and restaurant rows stay in place.

Similarity metric: cosine. TiDB queries use VEC_COSINE_DISTANCE, which is
1 - cosine similarity. Application scores then map that cosine onto [0, 1].
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.restaurants.embeddings import EMBEDDING_DIMENSION

revision: str = "0004_restaurant_embeddings"
down_revision: Union[str, Sequence[str], None] = "0003_fair_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not _column_exists("semantic_text"):
        op.add_column("restaurants", sa.Column("semantic_text", sa.Text(), nullable=True))
    if not _column_exists("semantic_text_hash"):
        op.add_column("restaurants", sa.Column("semantic_text_hash", sa.String(length=64), nullable=True))
    if not _column_exists("embedding_json"):
        op.add_column("restaurants", sa.Column("embedding_json", sa.Text(), nullable=True))
    if _supports_vector() and not _column_exists("embedding"):
        op.execute(f"ALTER TABLE restaurants ADD COLUMN embedding VECTOR({EMBEDDING_DIMENSION})")
    if _supports_vector() and _column_exists("embedding") and not _vector_index_exists():
        # TiDB Cloud needs a columnar replica before a vector index. The distance
        # function still works without the index, so a rejected index does not
        # fail the migration.
        try:
            op.execute(
                "ALTER TABLE restaurants ADD VECTOR INDEX idx_restaurants_embedding "
                "((VEC_COSINE_DISTANCE(embedding))) ADD_COLUMNAR_REPLICA_ON_DEMAND"
            )
        except Exception:
            pass


def downgrade() -> None:
    # Raw SQL avoids SQLAlchemy trying to parse the TiDB VECTOR type.
    # The vector index has to go before the column it covers.
    if _vector_index_exists():
        op.execute("ALTER TABLE restaurants DROP INDEX idx_restaurants_embedding")
    if _column_exists("embedding"):
        op.execute("ALTER TABLE restaurants DROP COLUMN embedding")
    if _column_exists("embedding_json"):
        op.drop_column("restaurants", "embedding_json")
    if _column_exists("semantic_text_hash"):
        op.drop_column("restaurants", "semantic_text_hash")
    if _column_exists("semantic_text"):
        op.drop_column("restaurants", "semantic_text")


def _supports_vector() -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return False
    version = bind.execute(sa.text("SELECT VERSION()")).scalar()
    return "tidb" in str(version or "").lower()


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


def _vector_index_exists() -> bool:
    bind = op.get_bind()
    count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'restaurants' "
            "AND index_name = 'idx_restaurants_embedding'"
        )
    ).scalar()
    return bool(count)
