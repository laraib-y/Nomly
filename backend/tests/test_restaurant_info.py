"""Phase 7.1: restaurant contact details come from the provider or stay empty."""

import pytest

from app.services.restaurants.geoapify import normalize_geoapify_feature
from app.services.restaurants.mock import MockRestaurantProvider
from app.services.restaurants.restaurant_normalizer import clean_phone, safe_web_url
from tests.helpers import create_dinner


def _feature(**properties) -> dict:
    return {"properties": {"name": "DooBoo", "place_id": "dooboo-1", "lat": 49.25, "lon": -122.98, **properties}}


def test_geoapify_contact_phone_and_website_are_kept():
    restaurant = normalize_geoapify_feature(
        _feature(
            formatted="4500 Kingsway, Burnaby, BC V5H 2A9, Canada",
            contact={"phone": "+1 604-555-0134"},
            website="https://dooboo.example.com/",
            categories=["catering.restaurant.korean"],
        )
    )
    assert restaurant is not None
    assert restaurant.phone == "+1 604-555-0134"
    assert restaurant.website == "https://dooboo.example.com/"
    assert restaurant.address == "4500 Kingsway, Burnaby, BC V5H 2A9, Canada"
    assert (restaurant.latitude, restaurant.longitude) == (49.25, -122.98)
    assert restaurant.cuisine == "Korean"


def test_raw_osm_tags_are_used_when_top_level_fields_are_missing():
    restaurant = normalize_geoapify_feature(
        _feature(datasource={"raw": {"phone": "+1 604 555 0199;+1 604 555 0100", "contact:website": "www.dooboo.example"}})
    )
    assert restaurant is not None
    assert restaurant.phone == "+1 604 555 0199"
    assert restaurant.website == "https://www.dooboo.example"


def test_missing_contact_details_stay_empty_and_nothing_is_invented():
    restaurant = normalize_geoapify_feature(_feature())
    assert restaurant is not None
    assert restaurant.phone is None
    assert restaurant.website is None
    assert restaurant.price is None
    assert restaurant.rating is None
    assert restaurant.image_url is None


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com",
        "https://user:pass@example.com",
        "https://exa mple.com",
        "https://",
        "example.com",
        "",
        None,
        42,
    ],
)
def test_unsafe_or_malformed_urls_are_rejected(url):
    assert safe_web_url(url) is None


def test_unsafe_provider_website_and_image_never_reach_the_candidate():
    restaurant = normalize_geoapify_feature(
        _feature(website="javascript:alert(document.cookie)", image="data:image/png;base64,AAAA")
    )
    assert restaurant is not None
    assert restaurant.website is None
    assert restaurant.image_url is None


def test_safe_urls_are_kept_unchanged():
    assert safe_web_url("https://example.com/menu?x=1") == "https://example.com/menu?x=1"
    assert safe_web_url("http://example.com") == "http://example.com"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+1 604-555-0134", "+1 604-555-0134"),
        ("(604) 555-0134", "(604) 555-0134"),
        ("+1 604 555 0134; +1 604 555 0135", "+1 604 555 0134"),
        ("call us", None),
        ("123", None),
        ("", None),
        (None, None),
        ("+1 604 555 0134 <script>", None),
    ],
)
def test_phone_cleaning(raw, expected):
    assert clean_phone(raw) == expected


def test_api_deck_and_results_carry_contact_fields_without_secrets(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sentinel-elevenlabs-key-0000")
    original = MockRestaurantProvider.collect

    def with_contact(self, intent):
        found = original(self, intent)
        return [
            item.model_copy(update={"phone": "+1 604-555-0134", "website": "https://contact.example.com"})
            if index == 0
            else item
            for index, item in enumerate(found)
        ]

    monkeypatch.setattr(MockRestaurantProvider, "collect", with_contact)
    created = create_dinner(client, nickname="Abdalla", group_size=1)
    code, pid = created["room_code"], created["participant"]["id"]
    assert client.post(f"/api/sessions/{code}/start", json={"participant_id": pid}).status_code == 200
    deck_response = client.get(f"/api/sessions/{code}/restaurants", params={"participant_id": pid})
    deck = deck_response.json()

    with_phone = [item for item in deck if item["phone"]]
    assert with_phone, "the restaurant with provider contact details should be in the deck"
    assert with_phone[0]["website"] == "https://contact.example.com"
    for item in deck:
        assert set(("phone", "website", "address", "latitude", "longitude", "price", "rating", "image_url")) <= item.keys()
        if item not in with_phone:
            assert item["phone"] is None
            assert item["website"] is None

    for item in deck:
        decision = "like" if item["phone"] else "pass"
        client.post(
            f"/api/sessions/{code}/swipes",
            json={"participant_id": pid, "restaurant_id": item["id"], "decision": decision},
        )
    results_response = client.get(f"/api/sessions/{code}/results")
    top = results_response.json()["top_match"]
    assert top["phone"] == "+1 604-555-0134"
    assert top["website"] == "https://contact.example.com"
    assert top["latitude"] is not None and top["longitude"] is not None
    assert top["satisfaction_percent"] == 100

    for text in (deck_response.text, results_response.text, client.get(f"/api/sessions/{code}").text):
        assert "sentinel-elevenlabs-key-0000" not in text
        assert "apiKey" not in text
        assert "api.geoapify.com" not in text
