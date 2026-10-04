import httpx

from app.core.config import get_settings
from app.schemas.ai import DinnerIntent
from app.services.restaurants.factory import get_restaurant_provider
from app.services.restaurants.geoapify import GeoapifyRestaurantProvider, normalize_geoapify_feature
from app.services.restaurants.mock import MockRestaurantProvider


SAMPLE_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-122.9805, 49.2488]},
    "properties": {
        "name": "Kinjo Sushi",
        "formatted": "4500 Kingsway, Burnaby, BC",
        "place_id": "geo-kinjo",
        "categories": ["catering", "catering.restaurant", "catering.restaurant.japanese"],
        "datasource": {"raw": {"rating": "4.6", "price_level": 2}},
        "lat": 49.2488,
        "lon": -122.9805,
    },
}


def test_normalize_geoapify_feature():
    restaurant = normalize_geoapify_feature(SAMPLE_FEATURE)
    assert restaurant is not None
    assert restaurant.external_id == "geo-kinjo"
    assert restaurant.name == "Kinjo Sushi"
    assert restaurant.cuisine == "Japanese"
    assert restaurant.price == 2
    assert restaurant.rating == 4.6
    assert restaurant.latitude == 49.2488
    assert restaurant.longitude == -122.9805
    assert restaurant.address == "4500 Kingsway, Burnaby, BC"
    assert restaurant.source == "geoapify"


def test_normalize_skips_places_without_a_name():
    assert normalize_geoapify_feature({"properties": {"formatted": "Somewhere"}}) is None


def test_mock_provider_prefers_requested_cuisine():
    provider = MockRestaurantProvider()
    results = provider.search(
        DinnerIntent(cuisines=["Japanese", "Korean"], location="Burnaby", price_level=2, vibe="casual")
    )
    assert len(results) == 12
    assert results[0].cuisine in {"Japanese", "Korean"}
    assert all(item.source == "mock" for item in results)
    assert all("Burnaby" in (item.address or "") for item in results)


def test_provider_factory_without_key_uses_mock():
    get_settings.cache_clear()
    provider = get_restaurant_provider()
    assert isinstance(provider, MockRestaurantProvider)


def test_geoapify_falls_back_when_request_fails():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "upstream down"})

    provider = GeoapifyRestaurantProvider(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    results = provider.search(DinnerIntent(location="Burnaby", cuisines=["Japanese"]))
    assert len(results) >= 10
    assert all(item.source == "mock" for item in results)


def test_geoapify_falls_back_when_api_key_is_blank():
    provider = GeoapifyRestaurantProvider(api_key="  ")
    results = provider.search(DinnerIntent(location="Burnaby"))
    assert len(results) >= 10
    assert all(item.source == "mock" for item in results)


def test_geoapify_normalizes_a_live_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        if "geocode" in str(request.url):
            return httpx.Response(200, json={"results": [{"lat": 49.25, "lon": -122.98}]})
        return httpx.Response(200, json={"features": [SAMPLE_FEATURE] * 10})

    provider = GeoapifyRestaurantProvider(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    results = provider.search(DinnerIntent(location="Burnaby", cuisines=["Japanese"], radius=5000))
    assert results[0].name == "Kinjo Sushi"
    assert results[0].source == "geoapify"
    assert 10 <= len(results) <= 15
