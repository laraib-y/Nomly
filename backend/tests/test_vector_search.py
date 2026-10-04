import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Restaurant
from app.services.restaurants.embeddings import (
    EMBEDDING_DIMENSION,
    MockEmbeddingProvider,
    cosine_similarity,
    normalize_similarity,
    similarity_from_cosine_distance,
)
from app.services.restaurants.semantic_search import (
    SemanticSearchError,
    rank_by_cosine,
    search_stored_embeddings,
    tidb_vector_search,
    vector_literal,
)


def test_closest_restaurant_is_first_and_scores_are_normalized():
    query = [1.0, 0.0, 0.0]
    hits = rank_by_cosine(
        query,
        [
            ("far", [0.0, 1.0, 0.0]),
            ("near", [1.0, 0.0, 0.0]),
            ("opposite", [-1.0, 0.0, 0.0]),
        ],
        limit=3,
    )
    assert [hit.restaurant_id for hit in hits] == ["near", "far", "opposite"]
    assert hits[0].similarity == 1.0
    assert hits[1].similarity == 0.5
    assert hits[2].similarity == 0.0
    assert all(0.0 <= hit.similarity <= 1.0 for hit in hits)


def test_similarity_order_is_deterministic_when_scores_tie():
    query = [1.0, 0.0]
    first = rank_by_cosine(query, [("b", [1.0, 0.0]), ("a", [1.0, 0.0])], limit=2)
    second = rank_by_cosine(query, [("b", [1.0, 0.0]), ("a", [1.0, 0.0])], limit=2)
    assert [hit.restaurant_id for hit in first] == ["a", "b"]
    assert [hit.restaurant_id for hit in second] == [hit.restaurant_id for hit in first]


def test_missing_and_wrong_dimension_embeddings_are_skipped():
    hits = rank_by_cosine([1.0, 0.0], [("bad", [1.0]), ("ok", [1.0, 0.0])], limit=5)
    assert [hit.restaurant_id for hit in hits] == ["ok"]


def test_cosine_distance_maps_onto_unit_interval():
    assert similarity_from_cosine_distance(0) == 1.0
    assert similarity_from_cosine_distance(1) == 0.5
    assert similarity_from_cosine_distance(2) == 0.0
    assert normalize_similarity(cosine_similarity([1.0, 0.0], [1.0, 0.0])) == 1.0


def test_vector_literal_rejects_the_wrong_dimension():
    try:
        vector_literal([0.1, 0.2])
    except Exception as exc:
        assert "dimension" in str(exc).lower() or exc.__class__.__name__ == "EmbeddingError"
    else:
        raise AssertionError("short vectors must be rejected")
    literal = vector_literal([0.0] * EMBEDDING_DIMENSION)
    assert literal.startswith("[")
    assert literal.endswith("]")


def test_tidb_search_rejects_a_short_query_before_sql():
    try:
        tidb_vector_search(None, [1.0, 0.0], ["restaurant-id"], limit=1)
    except SemanticSearchError as exc:
        assert "dimension" in str(exc).lower()
    else:
        raise AssertionError("short query must fail closed")


def test_json_embeddings_rank_the_closest_restaurant():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    embedder = MockEmbeddingProvider()
    query = embedder.embed_text("cozy quiet")
    near = Restaurant(
        external_id="near",
        name="Quiet Bowl",
        source="mock",
        embedding_json=json.dumps(query),
    )
    far = Restaurant(
        external_id="far",
        name="Loud Grill",
        source="mock",
        embedding_json=json.dumps(embedder.embed_text("lively nightclub")),
    )
    missing = Restaurant(external_id="missing", name="No Vector", source="mock")
    db.add_all([near, far, missing])
    db.commit()

    scores = search_stored_embeddings(
        db,
        query,
        [("mock", "near"), ("mock", "far"), ("mock", "missing")],
        limit=3,
    )
    assert scores["mock:near"] == 1.0
    assert scores["mock:near"] > scores["mock:far"]
    assert "mock:missing" not in scores
    db.close()
