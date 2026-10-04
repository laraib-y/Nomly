"""Blend structured relevance with soft semantic similarity.

Hard constraints and cuisine filtering happen before this step. This module
only reorders the restaurants it is given.

    final_score = structured_score * 0.75 + semantic_score * 0.25

Structured scores are on a 0–100 scale and are divided by 100 before blending.
Semantic scores are already normalized to [0, 1]. A restaurant with no embedding
scores 0.5 when other candidates have embeddings, so a missing vector is not a
penalty and is not a bonus. If nobody has an embedding, the structured order
is left unchanged.
"""

import logging

from sqlalchemy.orm import Session as DbSession

from app.schemas.ai import DinnerIntent
from app.services.restaurants.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingError,
    EmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
    normalize_similarity,
)
from app.services.restaurants.restaurant_ranker import ScoredRestaurant
from app.services.restaurants.semantic_search import (
    SemanticSearchError,
    rank_by_cosine,
    search_stored_embeddings,
)

logger = logging.getLogger(__name__)

STRUCTURED_WEIGHT = 0.75
SEMANTIC_WEIGHT = 0.25
STRUCTURED_SCORE_SCALE = 100.0
NEUTRAL_SEMANTIC_SCORE = 0.5


def build_semantic_query(intent: DinnerIntent) -> str | None:
    """Soft preference only. Cuisine, budget, and location stay structured."""

    vibe = " ".join((intent.vibe or "").split())
    if not vibe:
        return None
    return vibe


def apply_semantic_scores(
    ranked: list[ScoredRestaurant],
    similarities: dict[str, float],
) -> list[ScoredRestaurant]:
    if not similarities:
        return ranked
    blended: list[ScoredRestaurant] = []
    for item in ranked:
        key = _candidate_key(item)
        semantic = similarities.get(key, NEUTRAL_SEMANTIC_SCORE)
        semantic = max(0.0, min(1.0, semantic))
        structured = max(0.0, min(item.score / STRUCTURED_SCORE_SCALE, 1.0))
        combined = STRUCTURED_WEIGHT * structured + SEMANTIC_WEIGHT * semantic
        blended.append(ScoredRestaurant(item.restaurant, combined))
    blended.sort(
        key=lambda item: (
            -item.score,
            item.restaurant.name.lower(),
            item.restaurant.external_id,
        )
    )
    return blended


class SemanticRanker:
    """Looks up stored restaurant embeddings and blends them into the deck."""

    def __init__(
        self,
        db: DbSession | None = None,
        embedder: EmbeddingProvider | None = None,
        vectors: dict[str, list[float]] | None = None,
        search=None,
    ) -> None:
        self.db = db
        self.embedder = embedder
        self.vectors = vectors
        self.search = search

    def rerank(self, ranked: list[ScoredRestaurant], intent: DinnerIntent) -> list[ScoredRestaurant]:
        query_text = build_semantic_query(intent)
        if query_text is None:
            logger.info(
                "Semantic search skipped. Candidate count: %s. Embedding available: false. Fallback: false",
                len(ranked),
            )
            return ranked
        try:
            available = self._available(ranked)
        except Exception:
            logger.warning("Semantic search unavailable; using structured ranking fallback")
            return ranked
        if not available:
            logger.info(
                "Semantic search started. Candidate count: %s. Embedding available: false. "
                "Semantic results: 0. Fallback: true",
                len(ranked),
            )
            return ranked
        embedder = self.embedder or get_embedding_provider()
        try:
            query_vector = embedder.embed_text(query_text)
        except EmbeddingError:
            logger.warning("Semantic search unavailable; using structured ranking fallback")
            return ranked
        if len(query_vector) != EMBEDDING_DIMENSION:
            logger.warning("Semantic search unavailable; using structured ranking fallback")
            return ranked
        try:
            similarities = self._similarities(ranked, query_vector, available)
        except (SemanticSearchError, EmbeddingError):
            logger.warning("Semantic search unavailable; using structured ranking fallback")
            return ranked
        except Exception:
            logger.warning("Semantic search unavailable; using structured ranking fallback")
            return ranked
        if not similarities:
            logger.info(
                "Semantic search started. Candidate count: %s. Embedding available: true. "
                "Semantic results: 0. Fallback: true",
                len(ranked),
            )
            return ranked
        logger.info(
            "Semantic search started. Candidate count: %s. Embedding available: true. "
            "Vector search completed. Semantic results: %s. Fallback: false",
            len(ranked),
            len(similarities),
        )
        return apply_semantic_scores(ranked, similarities)

    def _available(self, ranked: list[ScoredRestaurant]) -> dict[str, list[float]]:
        if self.vectors is not None or self.search is not None:
            return dict(self.vectors or {})
        if self.db is None:
            return {}
        keys = [(_source(item), item.restaurant.external_id) for item in ranked]
        wanted = {f"{source}:{external_id}" for source, external_id in keys}
        from app.models import Restaurant

        rows = self.db.query(Restaurant).filter(Restaurant.embedding_json.is_not(None)).all()
        available: dict[str, list[float]] = {}
        for row in rows:
            key = f"{row.source}:{row.external_id}"
            if key not in wanted or not row.embedding_json:
                continue
            from app.services.restaurants.semantic_search import _parse_vector

            vector = _parse_vector(row.embedding_json)
            if vector is not None:
                available[key] = vector
        return available

    def _similarities(
        self,
        ranked: list[ScoredRestaurant],
        query_vector: list[float],
        available: dict[str, list[float]],
    ) -> dict[str, float]:
        if self.search is not None:
            return self.search(query_vector, ranked)
        if self.vectors is not None:
            pairs = [(key, vector) for key, vector in available.items()]
            hits = rank_by_cosine(query_vector, pairs, limit=len(pairs) or 1)
            return {hit.restaurant_id: hit.similarity for hit in hits}
        if self.db is None:
            return {}
        keys = [(_source(item), item.restaurant.external_id) for item in ranked]
        return search_stored_embeddings(self.db, query_vector, keys, limit=len(keys) or 1)


def _candidate_key(item: ScoredRestaurant) -> str:
    return f"{_source(item)}:{item.restaurant.external_id}"


def _source(item: ScoredRestaurant) -> str:
    return item.restaurant.source or ""


def score_vectors(query: list[float], vector: list[float]) -> float:
    return normalize_similarity(cosine_similarity(query, vector))
