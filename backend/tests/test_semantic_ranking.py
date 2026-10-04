import logging

from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate
from app.services.restaurants.base import RestaurantProvider
from app.services.restaurants.embeddings import EmbeddingError, MockEmbeddingProvider
from app.services.restaurants.restaurant_ranker import RankWeights, ScoredRestaurant
from app.services.restaurants.restaurant_search_service import RestaurantSearchService
from app.services.restaurants.semantic_rank import (
    SEMANTIC_WEIGHT,
    STRUCTURED_WEIGHT,
    apply_semantic_scores,
    build_semantic_query,
)
from app.services.restaurants.semantic_search import SemanticSearchError


class Catalog(RestaurantProvider):
    def __init__(self, places: list[RestaurantCandidate]) -> None:
        self.places = places

    def search(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        return self.places


def _place(
    name: str,
    cuisine: str,
    price: int | None,
    rating: float,
    external_id: str,
    latitude: float = 49.2488,
    longitude: float = -122.9805,
    description: str | None = None,
    categories: list[str] | None = None,
) -> RestaurantCandidate:
    return RestaurantCandidate(
        external_id=external_id,
        name=name,
        cuisine=cuisine,
        categories=categories or [cuisine],
        price=price,
        rating=rating,
        latitude=latitude,
        longitude=longitude,
        address="Burnaby",
        description=description or name,
        source="mock",
    )


def test_semantic_query_keeps_hard_facts_out_of_the_vector():
    query = build_semantic_query(
        DinnerIntent(
            group_size=5,
            location="Burnaby",
            cuisines=["Korean"],
            price_level=1,
            vibe="cozy and quiet",
        )
    )
    assert query == "cozy and quiet"
    assert "Korean" not in query
    assert "Burnaby" not in query
    assert "cheap" not in query


def test_structured_weights_stay_authoritative():
    assert STRUCTURED_WEIGHT == 0.75
    assert SEMANTIC_WEIGHT == 0.25
    assert STRUCTURED_WEIGHT + SEMANTIC_WEIGHT == 1
    weights = RankWeights()
    assert weights.cuisine + weights.price + weights.location + weights.rating + weights.category == 100


def test_semantic_relevance_can_improve_order_without_erasing_structure():
    quiet = _place("Quiet Bowl", "Korean", 2, 4.2, "quiet")
    loud = _place("Loud Grill", "Korean", 2, 4.4, "loud")
    improved = apply_semantic_scores(
        [ScoredRestaurant(loud, 82), ScoredRestaurant(quiet, 80)],
        {"mock:quiet": 1.0, "mock:loud": 0.0},
    )
    assert [item.restaurant.external_id for item in improved] == ["quiet", "loud"]

    strong = _place("Strong Match", "Korean", 2, 4.8, "strong")
    weak = _place("Weak Match", "Burgers", 2, 4.0, "weak")
    structured_wins = apply_semantic_scores(
        [ScoredRestaurant(strong, 100), ScoredRestaurant(weak, 40)],
        {"mock:strong": 0.0, "mock:weak": 1.0},
    )
    assert structured_wins[0].restaurant.external_id == "strong"


def test_ties_are_deterministic():
    alpha = _place("Alpha", "Korean", 2, 4.0, "b")
    bravo = _place("Alpha", "Korean", 2, 4.0, "a")
    first = apply_semantic_scores(
        [ScoredRestaurant(alpha, 80), ScoredRestaurant(bravo, 80)],
        {"mock:b": 0.4, "mock:a": 0.4},
    )
    second = apply_semantic_scores(
        [ScoredRestaurant(bravo, 80), ScoredRestaurant(alpha, 80)],
        {"mock:a": 0.4, "mock:b": 0.4},
    )
    assert [item.restaurant.external_id for item in first] == ["a", "b"]
    assert [item.restaurant.external_id for item in second] == ["a", "b"]


def test_budget_radius_and_diet_block_a_perfect_semantic_match():
    embedder = MockEmbeddingProvider()
    cozy = embedder.embed_text("cozy and quiet")
    other = embedder.embed_text("lively nightclub")
    pricey = _place("Pricey", "Korean", 4, 4.9, "pricey")
    cheap = _place("Cheap", "Korean", 1, 4.2, "cheap")
    far = _place("Far", "Korean", 1, 4.9, "far", latitude=49.45, longitude=-123.15)
    near = _place("Near", "Korean", 1, 4.2, "near")
    steak = _place("Steakhouse", "Korean", 2, 4.9, "steak", description="Steakhouse grill")
    bowl = _place("Green Bowl", "Korean", 2, 4.2, "bowl", description="Vegetarian bowls", categories=["Korean", "Vegetarian"])

    from app.services.restaurants.semantic_rank import SemanticRanker

    def deck(places, intent, center=None):
        ranker = SemanticRanker(
            embedder=embedder,
            vectors={
                "mock:pricey": cozy,
                "mock:far": cozy,
                "mock:steak": cozy,
                "mock:cheap": other,
                "mock:near": other,
                "mock:bowl": other,
            },
        )
        return RestaurantSearchService(Catalog(places), semantic=ranker).build_deck(intent, center=center)

    budget = deck([pricey, cheap], DinnerIntent(vibe="cozy and quiet", price_level=1))
    assert [item.external_id for item in budget] == ["cheap"]

    center = (49.2488, -122.9805)
    radius = deck([far, near], DinnerIntent(vibe="cozy and quiet", radius=2000), center=center)
    assert [item.external_id for item in radius] == ["near"]

    diet = deck(
        [steak, bowl],
        DinnerIntent(vibe="cozy and quiet", dietary_preferences=["vegetarian"]),
    )
    assert [item.external_id for item in diet] == ["bowl"]


def test_embedding_and_vector_failures_keep_the_structured_deck(caplog):
    from app.services.restaurants.semantic_rank import SemanticRanker

    places = [
        _place("Alpha", "Korean", 2, 4.8, "alpha"),
        _place("Bravo", "Korean", 2, 4.2, "bravo"),
    ]
    intent = DinnerIntent(cuisines=["Korean"], vibe="cozy and quiet")
    structured = [item.external_id for item in RestaurantSearchService(Catalog(places)).build_deck(intent)]

    class Boom:
        def embed_text(self, text: str) -> list[float]:
            raise EmbeddingError("down")

    embed_failed = RestaurantSearchService(
        Catalog(places),
        semantic=SemanticRanker(embedder=Boom(), vectors={"mock:bravo": [0.0] * 768}),
    ).build_deck(intent)

    def explode(query, ranked):
        raise SemanticSearchError("vector down")

    vector_failed = RestaurantSearchService(
        Catalog(places),
        semantic=SemanticRanker(
            embedder=MockEmbeddingProvider(),
            vectors={"mock:bravo": MockEmbeddingProvider().embed_text("cozy and quiet")},
            search=explode,
        ),
    ).build_deck(intent)

    assert [item.external_id for item in embed_failed] == structured
    assert [item.external_id for item in vector_failed] == structured
    assert "Semantic search unavailable; using structured ranking fallback" in caplog.text
    assert "secret" not in caplog.text.lower()


def test_missing_embeddings_do_not_call_the_provider(caplog):
    from app.services.restaurants.semantic_rank import SemanticRanker

    class Boom:
        def embed_text(self, text: str) -> list[float]:
            raise AssertionError("query embedding is not needed without restaurant vectors")

    places = [_place("Alpha", "Korean", 2, 4.5, "alpha")]
    with caplog.at_level(logging.INFO):
        deck = RestaurantSearchService(
            Catalog(places),
            semantic=SemanticRanker(embedder=Boom(), vectors={}),
        ).build_deck(DinnerIntent(vibe="cozy"))
    assert [item.external_id for item in deck] == ["alpha"]
    assert "Fallback: true" in caplog.text
