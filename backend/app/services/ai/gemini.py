import json
import logging
import re
import time

import httpx
from pydantic import ValidationError

from app.schemas.ai import DinnerIntent, apply_explicit_fields
from app.services.ai.base import AIService

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PROMPT = """Extract a dinner search intent from the user's request.

Return JSON only, with exactly these keys:
- group_size: integer 1-20, or null
- location: string, or null
- radius: integer meters, or null
- cuisines: array of cuisine names, or []
- price_level: integer 1-4, or null
- vibe: short phrase, or null
- dietary_preferences: array of short labels, or []

Rules:
- Extract only what the user stated. If a field was not mentioned, use null or [].
- Do not invent a city, neighbourhood, radius, price, vibe, group size, or diet.
- Do not guess a location from general knowledge.
- Do not name, rank, or recommend restaurants. Do not add restaurant fields.
- radius is meters, and only when the user states a distance. 5 km is 5000. 3 km is 3000. "Close by" is null. Never return the kilometer count itself.
- price_level 1 is cheap, budget, student budget, or affordable.
- price_level 2 is "not too expensive".
- price_level 3 is mid-range or moderate.
- price_level 4 is expensive or fine dining.
- "We don't care about price" is null.
- vibe is the atmosphere they asked for, such as "cozy" or "casual and relaxed". It is not a fact about a restaurant.
- dietary_preferences may include vegetarian, vegan, halal, kosher, or gluten-free when stated.
- An allergy mention is only a label such as "peanut allergy". Do not say a restaurant is safe.
- Use common cuisine names such as Japanese, Korean, Chinese, Thai, Indian, Vietnamese, Italian, or Mexican.
- Do not invent a cuisine category that is not a normal restaurant cuisine.
"""


class AIParseError(Exception):
    """Gemini responded, but the payload was not a valid dinner intent."""


class GeminiAIService(AIService):
    """Calls Gemini and validates the JSON against DinnerIntent.

    The API key stays in this service. Callers never see provider errors; they
    receive AIParseError and can fall back to the deterministic parser.
    """

    def __init__(self, api_key: str, client: httpx.Client | None = None, model: str = GEMINI_MODEL) -> None:
        self.api_key = api_key
        self._client = client
        self.model = model

    def parse_dinner_request(self, description: str, location: str | None = None) -> DinnerIntent:
        intent = self._request_intent(description)
        return apply_explicit_fields(intent, location=location)

    def _request_intent(self, description: str) -> DinnerIntent:
        payload = {
            "systemInstruction": {"parts": [{"text": _PROMPT}]},
            "contents": [{"parts": [{"text": description.strip()}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingLevel": "LOW"},
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "group_size": {"type": "INTEGER", "nullable": True},
                        "location": {"type": "STRING", "nullable": True},
                        "radius": {"type": "INTEGER", "nullable": True},
                        "cuisines": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "price_level": {"type": "INTEGER", "nullable": True},
                        "vibe": {"type": "STRING", "nullable": True},
                        "dietary_preferences": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": [
                        "group_size",
                        "location",
                        "radius",
                        "cuisines",
                        "price_level",
                        "vibe",
                        "dietary_preferences",
                    ],
                },
            },
        }
        url = GEMINI_URL.format(model=self.model)
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            body = self._post_intent(client, url, payload)
        finally:
            if owns_client:
                client.close()

        try:
            parsed = json.loads(_strip_fences(_extract_text(body)))
        except json.JSONDecodeError as exc:
            raise AIParseError("Gemini did not return JSON") from exc
        if not isinstance(parsed, dict):
            raise AIParseError("Gemini JSON must be an object")
        try:
            return DinnerIntent.model_validate(parsed)
        except ValidationError as exc:
            raise AIParseError("Gemini JSON did not match DinnerIntent") from exc

    def _post_intent(self, client: httpx.Client, url: str, payload: dict) -> dict:
        for attempt in range(2):
            try:
                response = client.post(url, headers={"x-goog-api-key": self.api_key}, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 503 and attempt == 0:
                    logger.warning("Gemini request failed status=503 model=%s; retrying once", self.model)
                    time.sleep(1)
                    continue
                logger.warning(
                    "Gemini request failed status=%s model=%s response=%s",
                    exc.response.status_code,
                    self.model,
                    _safe_response_body(exc.response.text, self.api_key),
                )
                raise AIParseError("Gemini request failed") from None
            except httpx.HTTPError as exc:
                logger.warning("Gemini request failed model=%s error_type=%s", self.model, type(exc).__name__)
                raise AIParseError("Gemini request failed") from None
        raise AIParseError("Gemini request failed")


def _extract_text(body: dict) -> str:
    try:
        parts = body["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIParseError("Gemini response did not include text") from exc
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict) or part.get("thought") is True:
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    if not texts:
        raise AIParseError("Gemini response text was empty")
    return texts[-1]


def _safe_response_body(text: str, api_key: str) -> str:
    clipped = " ".join(text.split())[:500]
    if api_key:
        clipped = clipped.replace(api_key, "***")
    return clipped


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned
