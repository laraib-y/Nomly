import json
import re

import httpx

from app.schemas.ai import DinnerIntent
from app.services.ai.base import AIService

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class AIParseError(Exception):
    """Gemini responded, but the payload was not a valid dinner intent."""


class GeminiAIService(AIService):
    """Calls Gemini and validates the JSON against DinnerIntent."""

    def __init__(self, api_key: str, client: httpx.Client | None = None, model: str = GEMINI_MODEL) -> None:
        self.api_key = api_key
        self._client = client
        self.model = model

    def parse_dinner_request(self, description: str, location: str | None = None) -> DinnerIntent:
        prompt = _prompt(description, location)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        url = GEMINI_URL.format(model=self.model)
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=12.0)
        try:
            response = client.post(url, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise AIParseError("Gemini request failed") from exc
        finally:
            if owns_client:
                client.close()

        text = _extract_text(body)
        try:
            parsed = json.loads(_strip_fences(text))
        except json.JSONDecodeError as exc:
            raise AIParseError("Gemini did not return JSON") from exc
        if not isinstance(parsed, dict):
            raise AIParseError("Gemini JSON must be an object")
        return DinnerIntent.model_validate(parsed)


def _prompt(description: str, location: str | None) -> str:
    hint = location.strip() if location else "none"
    return (
        "Convert the dinner request into JSON with exactly these keys: "
        "group_size (integer 1-20 or null), "
        "cuisines (array of cuisine names), price_level (integer 1-4 or null), "
        "location (string or null), radius (integer meters, default 5000), "
        "vibe (short string or null), "
        "dietary_preferences (array of short labels such as vegetarian, or empty). "
        "price_level 1 is cheapest and 4 is most expensive. "
        "Do not include any other keys or commentary.\n"
        f"Location hint: {hint}\n"
        f"Dinner request: {description.strip()}"
    )


def _extract_text(body: dict) -> str:
    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = parts[0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIParseError("Gemini response did not include text") from exc
    if not isinstance(text, str) or not text.strip():
        raise AIParseError("Gemini response text was empty")
    return text


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned
