"""Refresh restaurant embeddings when the grounded semantic text changes.

Run from the backend directory:

    python -m app.services.restaurants.refresh_embeddings

Room creation does not call this. It only embeds the diner's soft preference
when stored restaurant vectors already exist.
"""

import json
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session as DbSession

from app.core.database import open_session
from app.models import Restaurant
from app.services.restaurants.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingError,
    EmbeddingProvider,
    get_embedding_provider,
)
from app.services.restaurants.semantic_search import SemanticSearchError, write_stored_vector
from app.services.restaurants.semantic_text import build_restaurant_semantic_text, semantic_text_hash

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RefreshReport:
    updated: int
    skipped: int
    failed: int


def refresh_embeddings(db: DbSession, embedder: EmbeddingProvider) -> RefreshReport:
    updated = 0
    skipped = 0
    failed = 0
    restaurants = db.query(Restaurant).order_by(Restaurant.id.asc()).all()
    for restaurant in restaurants:
        text = build_restaurant_semantic_text(restaurant)
        digest = semantic_text_hash(text)
        if restaurant.semantic_text_hash == digest and _vector_is_current(restaurant.embedding_json):
            skipped += 1
            continue
        if not text.strip():
            failed += 1
            logger.warning("Embedding refresh skipped a restaurant with no semantic text")
            continue
        try:
            vector = embedder.embed_text(text)
            if len(vector) != EMBEDDING_DIMENSION:
                raise EmbeddingError("Unexpected embedding dimension")
        except EmbeddingError:
            failed += 1
            logger.warning("Embedding refresh failed for restaurant %s", restaurant.id)
            continue
        restaurant.semantic_text = text
        restaurant.semantic_text_hash = digest
        restaurant.embedding_json = json.dumps(vector)
        try:
            write_stored_vector(db, restaurant.id, vector)
        except SemanticSearchError:
            logger.warning("TiDB vector write failed for restaurant %s", restaurant.id)
        updated += 1
    db.commit()
    logger.info(
        "Embedding refresh finished. updated=%s skipped=%s failed=%s",
        updated,
        skipped,
        failed,
    )
    return RefreshReport(updated=updated, skipped=skipped, failed=failed)


def _vector_is_current(raw: str | None) -> bool:
    if not raw:
        return False
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list) and len(parsed) == EMBEDDING_DIMENSION


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    db = open_session()
    try:
        report = refresh_embeddings(db, get_embedding_provider())
    finally:
        db.close()
    print(f"updated={report.updated} skipped={report.skipped} failed={report.failed}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
