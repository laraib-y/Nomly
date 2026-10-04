"""Semantic similarity over the eligible restaurant set.

TiDB vector search is used when the VECTOR column exists. Otherwise the same
cosine metric runs in Python over embedding JSON. Either path returns
normalized scores in [0, 1]. A failure does not invent restaurants.
"""

import json
import logging
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session as DbSession

from app.models import Restaurant
from app.services.restaurants.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingError,
    cosine_similarity,
    normalize_similarity,
    similarity_from_cosine_distance,
)

logger = logging.getLogger(__name__)

_vector_column: bool | None = None


class SemanticSearchError(Exception):
    """Vector search could not be completed."""


@dataclass(frozen=True)
class SemanticHit:
    restaurant_id: str
    similarity: float


def rank_by_cosine(
    query: list[float],
    items: list[tuple[str, list[float]]],
    limit: int,
) -> list[SemanticHit]:
    scored: list[SemanticHit] = []
    for restaurant_id, vector in items:
        if len(vector) != len(query):
            continue
        try:
            similarity = normalize_similarity(cosine_similarity(query, vector))
        except EmbeddingError:
            continue
        scored.append(SemanticHit(restaurant_id, similarity))
    scored.sort(key=lambda hit: (-hit.similarity, hit.restaurant_id))
    if limit < 0:
        return []
    return scored[:limit]


def vector_column_available(db: DbSession) -> bool:
    """True only when this server has restaurants.embedding as a TiDB vector."""

    global _vector_column
    if _vector_column is not None:
        return _vector_column
    bind = db.get_bind()
    if bind.dialect.name != "mysql":
        _vector_column = False
        return False
    try:
        count = db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'restaurants' "
                "AND column_name = 'embedding'"
            )
        ).scalar()
        _vector_column = bool(count)
    except Exception:
        _vector_column = False
    return _vector_column


def clear_stored_vector(db: DbSession, restaurant_id: str) -> None:
    if not restaurant_id or not vector_column_available(db):
        return
    try:
        with db.begin_nested():
            db.execute(
                text("UPDATE restaurants SET embedding = NULL WHERE id = :restaurant_id"),
                {"restaurant_id": restaurant_id},
            )
    except Exception:
        logger.warning("Semantic search unavailable; using structured ranking fallback")


def write_stored_vector(db: DbSession, restaurant_id: str, vector: list[float]) -> None:
    if not vector_column_available(db):
        return
    if len(vector) != EMBEDDING_DIMENSION:
        raise EmbeddingError("Unexpected embedding dimension")
    try:
        with db.begin_nested():
            db.execute(
                text("UPDATE restaurants SET embedding = :embedding WHERE id = :restaurant_id"),
                {"embedding": vector_literal(vector), "restaurant_id": restaurant_id},
            )
    except Exception as exc:
        raise SemanticSearchError("Vector write failed") from exc


def search_stored_embeddings(
    db: DbSession,
    query: list[float],
    keys: list[tuple[str, str]],
    limit: int,
) -> dict[str, float]:
    """Return source:external_id to normalized similarity for stored vectors."""

    if len(query) != EMBEDDING_DIMENSION or not keys or limit <= 0:
        return {}
    wanted = {f"{source}:{external_id}" for source, external_id in keys}
    rows = db.query(Restaurant).filter(Restaurant.embedding_json.is_not(None)).all()
    parsed: list[tuple[str, list[float]]] = []
    id_to_key: dict[str, str] = {}
    for row in rows:
        key = f"{row.source}:{row.external_id}"
        if key not in wanted:
            continue
        vector = _parse_vector(row.embedding_json)
        if vector is None:
            continue
        parsed.append((key, vector))
        id_to_key[row.id] = key
    if not parsed:
        return {}
    if vector_column_available(db):
        try:
            hits = tidb_vector_search(db, query, list(id_to_key), limit)
        except SemanticSearchError:
            logger.warning("Semantic search unavailable; using structured ranking fallback")
            raise
        if hits:
            return {
                id_to_key[hit.restaurant_id]: hit.similarity
                for hit in hits
                if hit.restaurant_id in id_to_key
            }
    hits = rank_by_cosine(query, parsed, limit)
    return {hit.restaurant_id: hit.similarity for hit in hits}


def tidb_vector_search(
    db: DbSession,
    query: list[float],
    restaurant_ids: list[str],
    limit: int,
) -> list[SemanticHit]:
    if not restaurant_ids or limit <= 0:
        return []
    if len(query) != EMBEDDING_DIMENSION:
        raise SemanticSearchError("Unexpected embedding dimension")
    statement = text(
        """
        SELECT id, VEC_COSINE_DISTANCE(embedding, :query) AS distance
        FROM restaurants
        WHERE id IN :ids AND embedding IS NOT NULL
        ORDER BY distance ASC, id ASC
        LIMIT :limit
        """
    ).bindparams(bindparam("ids", expanding=True))
    try:
        with db.begin_nested():
            result = db.execute(
                statement,
                {"query": vector_literal(query), "ids": restaurant_ids, "limit": limit},
            )
            rows = result.all()
    except Exception as exc:
        raise SemanticSearchError("Vector search failed") from exc
    hits: list[SemanticHit] = []
    for row in rows:
        distance = row.distance
        if distance is None:
            continue
        hits.append(SemanticHit(str(row.id), similarity_from_cosine_distance(float(distance))))
    hits.sort(key=lambda hit: (-hit.similarity, hit.restaurant_id))
    return hits


def vector_literal(values: list[float]) -> str:
    if len(values) != EMBEDDING_DIMENSION:
        raise EmbeddingError("Unexpected embedding dimension")
    return "[" + ",".join(format(float(value), ".8f") for value in values) + "]"


def _parse_vector(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or len(parsed) != EMBEDDING_DIMENSION:
        return None
    try:
        return [float(value) for value in parsed]
    except (TypeError, ValueError):
        return None
