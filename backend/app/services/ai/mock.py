import re

from app.schemas.ai import DinnerIntent
from app.services.ai.base import AIService

_CUISINE_KEYWORDS: list[tuple[str, str]] = [
    ("korean", "Korean"),
    ("japanese", "Japanese"),
    ("sushi", "Japanese"),
    ("ramen", "Japanese"),
    ("izakaya", "Japanese"),
    ("italian", "Italian"),
    ("pizza", "Pizza"),
    ("mexican", "Mexican"),
    ("taco", "Mexican"),
    ("chinese", "Chinese"),
    ("thai", "Thai"),
    ("indian", "Indian"),
    ("vietnamese", "Vietnamese"),
    ("pho", "Vietnamese"),
    ("burger", "Burgers"),
    ("mediterranean", "Mediterranean"),
    ("seafood", "Seafood"),
    ("french", "French"),
    ("greek", "Greek"),
    ("american", "American"),
]

_VIBES = ("casual", "cozy", "fancy", "lively", "quiet", "romantic", "family")


class MockAIService(AIService):
    """Keyword parser used when Gemini is not configured or the request fails."""

    def parse_dinner_request(self, description: str, location: str | None = None) -> DinnerIntent:
        text = " ".join(description.lower().split())
        found: list[tuple[int, str]] = []
        for keyword, label in _CUISINE_KEYWORDS:
            index = text.find(keyword)
            if index >= 0 and all(existing != label for _position, existing in found):
                found.append((index, label))
        cuisines = [label for _index, label in sorted(found, key=lambda item: item[0])]

        price_level = _price_level(text)
        vibe = next((item for item in _VIBES if item in text), None)
        parsed_location = _location_from_text(description)
        chosen_location = " ".join(location.split()) if location and location.strip() else parsed_location

        return DinnerIntent(
            group_size=_group_size(text),
            cuisines=cuisines,
            price_level=price_level,
            location=chosen_location,
            radius=5000,
            vibe=vibe,
            dietary_preferences=_dietary(text),
        )


def _group_size(text: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*(?:people|person|friends|of us)\b", text)
    if not match:
        return None
    size = int(match.group(1))
    if 1 <= size <= 20:
        return size
    return None


def _dietary(text: str) -> list[str]:
    found: list[str] = []
    for label, pattern in (
        ("vegetarian", r"vegetarian"),
        ("vegan", r"vegan"),
        ("gluten-free", r"gluten[ -]?free"),
        ("halal", r"halal"),
    ):
        if re.search(pattern, text) and label not in found:
            found.append(label)
    return found


def _price_level(text: str) -> int | None:
    if re.search(r"fine dining|splurge|very expensive|upscale|fancy", text):
        return 4
    if re.search(r"cheap|budget|inexpensive|affordable|not too expensive|under \$?\d+", text):
        return 2
    if re.search(r"moderate|mid[- ]range", text):
        return 3
    return None


def _location_from_text(description: str) -> str | None:
    match = re.search(
        r"\b(?:around|near|in|at)\s+([A-Za-z][A-Za-z .'\-]{1,40}?)(?=,|\.|$)",
        description,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    location = " ".join(match.group(1).split())
    # Drop a trailing clause word if the sentence had no comma.
    for stopper in (" not ", " under ", " preferably ", " with "):
        index = location.lower().find(stopper.strip())
        if index > 0 and location.lower().startswith(stopper.strip()):
            continue
    return location[:80] or None
