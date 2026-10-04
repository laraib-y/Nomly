import httpx
import pytest

from app.core.exceptions import BadRequestError, ConflictError
from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate
from app.services.restaurants.base import RestaurantProvider, RestaurantProviderError
from app.services.restaurants.geoapify import (
    GeoapifyRestaurantProvider,
    _safe_error,
    build_places_params,
    categories_for_intent,
    normalize_geoapify_feature,
)
from app.services.restaurants.mock import MockRestaurantProvider
from app.services.restaurants.restaurant_normalizer import dedupe_restaurants
from app.services.restaurants.restaurant_ranker import (
    apply_hard_constraints,
    rank_candidates,
    select_diverse_deck,
)
from app.services.restaurants.restaurant_search_service import RestaurantSearchService
from tests.helpers import create_dinner, start_dinner


def _place(
    name: str,
    cuisine: str,
    price: int | None,
    rating: float | None,
    external_id: str | None = None,
    latitude: float | None = 49.2488,
    longitude: float | None = -122.9805,
    categories: list[str] | None = None,
) -> RestaurantCandidate:
    return RestaurantCandidate(
        external_id=external_id or name.lower().replace(" ", "-"),
        name=name,
        cuisine=cuisine,
        categories=categories or [cuisine],
        price=price,
        rating=rating,
        latitude=latitude,
        longitude=longitude,
        address="1 Main St",
        source="test",
    )


def test_geoapify_query_follows_cuisine_and_radius():
    japanese = categories_for_intent(DinnerIntent(cuisines=["Japanese"], location="Burnaby"))
    italian = categories_for_intent(DinnerIntent(cuisines=["Italian"], location="Vancouver"))
    assert "japanese" in japanese
    assert "italian" in italian
    assert japanese != italian
    params = build_places_params(49.2488, -122.9805, 4000, japanese, "test-key", 20)
    assert params["categories"] == japanese
    assert params["filter"] == "circle:-122.9805,49.2488,4000"
    assert params["limit"] == 20


def test_normalize_missing_fields_and_bad_coordinates():
    restaurant = normalize_geoapify_feature(
        {
            "properties": {
                "name": "Quiet Counter",
                "place_id": "quiet-1",
                "lat": 999,
                "lon": -122.9,
            }
        }
    )
    assert restaurant is not None
    assert restaurant.rating is None
    assert restaurant.price is None
    assert restaurant.image_url is None
    assert restaurant.address is None
    assert restaurant.latitude is None
    assert restaurant.longitude is None


def test_provider_failure_and_missing_key_use_mock_deck():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "upstream down"})

    failed = GeoapifyRestaurantProvider(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    blank = GeoapifyRestaurantProvider(api_key="")
    intent = DinnerIntent(cuisines=["Japanese"], location="Burnaby", price_level=2)
    for provider in (failed, blank):
        deck = RestaurantSearchService(provider).build_deck(intent)
        assert deck
        assert all(item.source == "mock" for item in deck)
        assert all(item.cuisine == "Japanese" for item in deck)
        assert all(item.price is None or item.price <= 2 for item in deck)


def test_error_text_redacts_api_keys():
    assert "super-secret" not in _safe_error(RuntimeError("GET places?apiKey=super-secret&limit=1"))


def test_valid_missing_and_radius_locations():
    burnaby = MockRestaurantProvider().collect(DinnerIntent(location="Burnaby, BC"))
    assert burnaby
    assert all("Burnaby" in (item.address or "") for item in burnaby)

    unspecified = MockRestaurantProvider().collect(DinnerIntent())
    assert unspecified
    assert all("Vancouver" in (item.address or "") for item in unspecified)

    center = (49.2488, -122.9805)
    near = _place("Near", "Japanese", 2, 4.5, latitude=49.249, longitude=-122.981)
    far = _place("Far", "Japanese", 2, 4.8, latitude=49.45, longitude=-123.15)
    kept = apply_hard_constraints([near, far], DinnerIntent(radius=2000), center)
    assert [item.name for item in kept] == ["Near"]

    with pytest.raises(BadRequestError) as exc:
        RestaurantSearchService(MockRestaurantProvider()).build_deck(DinnerIntent(location="12345"))
    assert exc.value.code == "INVALID_LOCATION"


def test_dedupes_same_external_id_and_nearby_names():
    original = _place("Jin's Korean Restaurant", "Korean", 2, 4.4, external_id="same-id")
    repeat = _place("Different Name", "Korean", 2, 4.2, external_id="same-id", latitude=49.3)
    twin = _place("Jins Korean Restaurant", "Korean", 2, 4.5, external_id="other-id", latitude=49.249)
    distant = _place(
        "Jin's Korean Restaurant",
        "Korean",
        2,
        4.1,
        external_id="far-id",
        latitude=49.35,
        longitude=-123.1,
    )
    kept = dedupe_restaurants([original, repeat, twin, distant])
    assert [item.external_id for item in kept] == ["same-id", "far-id"]


def test_price_fit_outranks_a_slightly_higher_rating():
    affordable = _place("Restaurant A", "Japanese", 2, 4.7)
    expensive = _place("Restaurant B", "Japanese", 4, 4.9)
    intent = DinnerIntent(cuisines=["Japanese"], price_level=2, location="Burnaby")
    ranked = rank_candidates([affordable, expensive], intent)
    assert ranked[0].restaurant.name == "Restaurant A"
    assert ranked[0].score > ranked[1].score
    filtered = apply_hard_constraints([affordable, expensive], intent)
    assert [item.name for item in filtered] == ["Restaurant A"]


def test_diversity_keeps_a_second_cuisine_in_the_deck():
    japanese = [_place(f"Japanese {index}", "Japanese", 2, 4.8, external_id=f"j-{index}") for index in range(20)]
    korean = [
        _place(f"Korean {index}", "Korean", 2, 4.0, external_id=f"k-{index}", latitude=49.25)
        for index in range(6)
    ]
    ranked = rank_candidates(japanese + korean, DinnerIntent(cuisines=["Japanese", "Korean"], price_level=2))
    deck = select_diverse_deck(ranked, limit=15)
    cuisines = {item.restaurant.cuisine for item in deck}
    assert cuisines == {"Japanese", "Korean"}
    assert len(deck) == 15


def test_deck_size_does_not_invent_restaurants():
    fifteen = [_place(f"Place {index}", "Japanese", 2, 4.0, external_id=f"p-{index}") for index in range(15)]
    seven = fifteen[:7]
    assert len(select_diverse_deck(rank_candidates(fifteen, DinnerIntent(cuisines=["Japanese"])))) == 15
    assert len(select_diverse_deck(rank_candidates(seven, DinnerIntent(cuisines=["Japanese"])))) == 7


def test_search_returns_fewer_when_only_a_few_match():
    deck = RestaurantSearchService(MockRestaurantProvider()).build_deck(
        DinnerIntent(cuisines=["Japanese"], location="Burnaby", price_level=2)
    )
    assert 1 <= len(deck) < 12
    assert all(item.cuisine == "Japanese" for item in deck)
    assert all(item.price is not None and item.price <= 2 for item in deck)


def test_empty_provider_and_fallback_raise_a_clear_error():
    class EmptyProvider(RestaurantProvider):
        def search(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
            return []

        def collect(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
            return []

    class DownProvider(RestaurantProvider):
        def search(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
            raise RestaurantProviderError("down")

        def collect(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
            raise RestaurantProviderError("down")

    with pytest.raises(ConflictError) as exc:
        RestaurantSearchService(EmptyProvider(), fallback=EmptyProvider()).build_deck(
            DinnerIntent(location="Burnaby")
        )
    assert exc.value.code == "NO_RESTAURANTS_FOUND"

    recovered = RestaurantSearchService(DownProvider()).build_deck(
        DinnerIntent(location="Burnaby", cuisines=["Korean"], price_level=2)
    )
    assert recovered
    assert all(item.source == "mock" and item.cuisine == "Korean" for item in recovered)


def test_session_stores_one_shared_deck(client):
    session = create_dinner(client)
    assert 10 <= session["restaurant_count"] <= 15
    _body, first = start_dinner(client, session)
    second = client.get(
        f"/api/sessions/{session['room_code']}/restaurants",
        params={"participant_id": session["participant"]["id"]},
    )
    assert second.status_code == 200
    assert [item["id"] for item in first] == [item["id"] for item in second.json()]
    assert all(item["price"] is None or item["price"] <= 2 for item in first)
    assert all(item["cuisine"] in {"Japanese", "Korean"} for item in first)
