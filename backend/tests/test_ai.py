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
    assert intent.radius == 5000
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
