import json

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.ai import DinnerIntent
from app.services.ai.base import AIService
from app.services.ai.factory import get_ai_service
from app.services.ai.gemini import AIParseError, GeminiAIService
from app.services.ai.mock import MockAIService
from app.services.sessions.session_service import SessionService
from app.services.matching.matching_service import MatchingService
from app.services.restaurants.mock import MockRestaurantProvider


def test_mock_ai_parses_the_sample_request():
    intent = MockAIService().parse_dinner_request(
        "We want somewhere casual around Burnaby, not too expensive, preferably Japanese or Korean.",
        location="Burnaby",
    )
    assert intent.cuisines == ["Japanese", "Korean"]
    assert intent.price_level == 2
    assert intent.location == "Burnaby"
    assert intent.radius is None
    assert intent.vibe == "casual"


def test_structured_output_validation():
    intent = DinnerIntent.model_validate(
        {
            "cuisines": "Japanese, Korean",
            "price_level": "2",
            "location": " Burnaby ",
            "radius": 5000,
            "vibe": "casual",
            "drop_this": "ignored",
        }
    )
    assert intent.cuisines == ["Japanese", "Korean"]
    assert intent.price_level == 2
    assert intent.location == "Burnaby"
    assert DinnerIntent().radius is None

    with pytest.raises(ValidationError):
        DinnerIntent(price_level=9)
    with pytest.raises(ValidationError):
        DinnerIntent(radius=10)


def test_gemini_service_interface():
    service = GeminiAIService("test-key")
    assert isinstance(service, AIService)


def test_gemini_parses_valid_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "test-key"
        payload = {
            "cuisines": ["Japanese", "Korean"],
            "price_level": 2,
            "location": "Burnaby",
            "radius": 5000,
            "vibe": "casual",
        }
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]},
        )

    service = GeminiAIService("test-key", client=httpx.Client(transport=httpx.MockTransport(handler)))
    intent = service.parse_dinner_request("Japanese or Korean around Burnaby", "Burnaby")
    assert intent.cuisines == ["Japanese", "Korean"]
    assert intent.price_level == 2
    assert intent.location == "Burnaby"


def test_gemini_rejects_invalid_json():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]},
        )

    service = GeminiAIService("test-key", client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AIParseError):
        service.parse_dinner_request("dinner", None)


def test_factory_uses_mock_without_a_key():
    get_settings.cache_clear()
    assert isinstance(get_ai_service(), MockAIService)


def test_session_create_falls_back_when_gemini_fails(client):
    class BoomAI(AIService):
        def parse_dinner_request(self, description: str, location: str | None = None) -> DinnerIntent:
            raise AIParseError("down")

    from app.main import app
    from app.api.deps import get_session_service
    from app.core.database import open_session

    def override():
        db = open_session()
        try:
            yield SessionService(
                db=db,
                ai=BoomAI(),
                restaurants=MockRestaurantProvider(),
                matching=MatchingService(),
            )
        finally:
            db.close()

    app.dependency_overrides[get_session_service] = override
    response = client.post(
        "/api/sessions",
        json={
            "description": "Casual Japanese around Burnaby, not too expensive.",
            "nickname": "Abdalla",
            "location": "Burnaby",
        },
    )
    app.dependency_overrides.pop(get_session_service, None)
    assert response.status_code == 201, response.text
    assert response.json()["intent"]["location"] == "Burnaby"
    assert "Japanese" in response.json()["intent"]["cuisines"]
    assert "gemini" not in response.text.lower()


def test_mock_extracts_location_and_cuisine_without_filling_the_rest():
    intent = MockAIService().parse_dinner_request("Find Japanese food in Burnaby.")
    assert intent.location == "Burnaby"
    assert intent.cuisines == ["Japanese"]
    assert intent.price_level is None
    assert intent.vibe is None
    assert intent.group_size is None
    assert intent.radius is None
    assert intent.dietary_preferences == []


def test_mock_extracts_multiple_cuisines_without_a_location():
    intent = MockAIService().parse_dinner_request("Japanese or Korean.")
    assert intent.cuisines == ["Japanese", "Korean"]
    assert intent.location is None
    assert intent.price_level is None
    assert intent.group_size is None


def test_mock_maps_cheap_to_the_low_price_level():
    intent = MockAIService().parse_dinner_request("Something cheap.")
    assert intent.price_level == 1
    assert intent.location is None
    assert intent.cuisines == []
    assert intent.vibe is None
    assert intent.group_size is None


def test_mock_keeps_a_vibe_phrase():
    intent = MockAIService().parse_dinner_request("Somewhere cozy and casual.")
    assert intent.vibe == "cozy and casual"
    assert intent.location is None
    assert intent.price_level is None


def test_mock_extracts_dietary_preference_without_a_group_size():
    intent = MockAIService().parse_dinner_request("One person is vegetarian.")
    assert intent.dietary_preferences == ["vegetarian"]
    assert intent.group_size is None
    assert intent.location is None


def test_mock_extracts_a_written_group_size():
    intent = MockAIService().parse_dinner_request("There are six of us.")
    assert intent.group_size == 6
    assert intent.location is None
    assert intent.cuisines == []
    assert intent.price_level is None
    assert intent.vibe is None


def test_mock_does_not_invent_missing_preferences():
    intent = MockAIService().parse_dinner_request("I want Japanese food.")
    assert intent.cuisines == ["Japanese"]
    assert intent.location is None
    assert intent.price_level is None
    assert intent.vibe is None
    assert intent.group_size is None
    assert intent.radius is None


def test_mock_extracts_named_places():
    assert MockAIService().parse_dinner_request("Near SFU").location == "SFU"
    assert MockAIService().parse_dinner_request("Downtown Vancouver").location == "Downtown Vancouver"
    assert MockAIService().parse_dinner_request("Around Burnaby").location == "Burnaby"


def test_mock_extracts_an_explicit_radius_only():
    stated = MockAIService().parse_dinner_request("Japanese food within 5 km.")
    nearby = MockAIService().parse_dinner_request("Something close by.")
    assert stated.radius == 5000
    assert stated.cuisines == ["Japanese"]
    assert nearby.radius is None
    assert nearby.location is None


def test_mock_reads_the_group_request_without_inventing_a_radius():
    intent = MockAIService().parse_dinner_request(
        "We're five students looking for something cheap around Burnaby, preferably Japanese or Korean, and somewhere casual."
    )
    assert intent.group_size == 5
    assert intent.location == "Burnaby"
    assert intent.cuisines == ["Japanese", "Korean"]
    assert intent.price_level == 1
    assert intent.vibe == "casual"
    assert intent.radius is None


def test_gemini_validation_failure_is_an_ai_parse_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps({"price_level": 9})}]}}]},
        )

    service = GeminiAIService("test-key", client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AIParseError):
        service.parse_dinner_request("Find Japanese food in Burnaby.")


def test_explicit_fields_override_gemini(client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "test-key" not in request.content.decode()
        payload = {
            "group_size": 2,
            "location": "Vancouver",
            "radius": None,
            "cuisines": ["Japanese"],
            "price_level": 1,
            "vibe": "lively",
            "dietary_preferences": [],
        }
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]},
        )

    _use_ai(client, GeminiAIService("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post(
        "/api/sessions",
        json={
            "description": "Find me a good sushi place in Burnaby.",
            "nickname": "Abdalla",
            "location": "Burnaby",
            "group_size": 6,
        },
    )
    assert response.status_code == 201, response.text
    intent = response.json()["intent"]
    assert intent["location"] == "Burnaby"
    assert intent["group_size"] == 6
    assert intent["cuisines"] == ["Japanese"]
    assert intent["vibe"] == "lively"
    assert intent["price_level"] == 1
    assert intent["radius"] is None
    assert 1 <= response.json()["restaurant_count"] <= 15
    assert "test-key" not in response.text

    started = client.post(
        f"/api/sessions/{response.json()['room_code']}/start",
        json={"participant_id": response.json()["participant"]["id"]},
    )
    assert started.status_code == 200, started.text
    restaurants = client.get(f"/api/sessions/{response.json()['room_code']}/restaurants")
    assert restaurants.status_code == 200, restaurants.text
    assert restaurants.json()
    assert all(place["cuisine"] == "Japanese" for place in restaurants.json())


@pytest.mark.parametrize(
    "transport_response",
    [
        httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]}),
        httpx.Response(429, json={"error": {"message": "rate limit"}}),
        httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"price_level": 99})}]}}]}),
    ],
)
def test_session_create_falls_back_when_gemini_output_is_unusable(client, transport_response):
    def handler(_request: httpx.Request) -> httpx.Response:
        return transport_response

    _use_ai(client, GeminiAIService("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post(
        "/api/sessions",
        json={
            "description": "Find Japanese food in Burnaby.",
            "nickname": "Abdalla",
        },
    )
    assert response.status_code == 201, response.text
    intent = response.json()["intent"]
    assert intent["location"] == "Burnaby"
    assert intent["cuisines"] == ["Japanese"]
    assert intent["price_level"] is None
    assert intent["group_size"] is None
    lowered = response.text.lower()
    assert "gemini" not in lowered
    assert "429" not in lowered
    assert "validation" not in lowered
    assert response.json()["restaurant_count"] >= 1


def _use_ai(client, ai: AIService) -> None:
    from app.main import app
    from app.api.deps import get_session_service
    from app.core.database import open_session

    def override():
        db = open_session()
        try:
            yield SessionService(
                db=db,
                ai=ai,
                restaurants=MockRestaurantProvider(),
                matching=MatchingService(),
            )
        finally:
            db.close()

    app.dependency_overrides[get_session_service] = override
    client.app = app
