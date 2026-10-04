import re

from app.schemas.ai import DinnerIntent, apply_explicit_fields
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

_VIBE_WORDS = ("casual", "cozy", "fancy", "lively", "quiet", "romantic", "relaxed", "family")
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
_NUMBER = (
    r"\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
)


class MockAIService(AIService):
    """Deterministic parser used when Gemini is not configured or the call fails."""

    def parse_dinner_request(self, description: str, location: str | None = None) -> DinnerIntent:
        text = " ".join(description.lower().split())
        intent = DinnerIntent(
            group_size=_group_size(text),
            cuisines=_cuisines(text),
            price_level=_price_level(text),
            location=_location_from_text(description),
            radius=_radius_meters(text),
            vibe=_vibe(text),
            dietary_preferences=_dietary(text),
        )
        return apply_explicit_fields(intent, location=location)


def _cuisines(text: str) -> list[str]:
    found: list[tuple[int, str]] = []
    for keyword, label in _CUISINE_KEYWORDS:
        index = text.find(keyword)
        if index >= 0 and all(existing != label for _position, existing in found):
            found.append((index, label))
    return [label for _index, label in sorted(found, key=lambda item: item[0])]


def _group_size(text: str) -> int | None:
    patterns = (
        rf"\b({_NUMBER})\s+(?:of us|people|friends|students|guests)\b",
        rf"\b(?:we(?:'re| are)|there are|there're|group of)\s+({_NUMBER})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match is None:
            continue
        size = _number_token(match.group(1))
        if size is not None:
            return size
    return None


def _number_token(token: str) -> int | None:
    if token.isdigit():
        size = int(token)
    else:
        size = _NUMBER_WORDS.get(token)
    if size is not None and 1 <= size <= 20:
        return size
    return None


def _dietary(text: str) -> list[str]:
    found: list[str] = []
    for label, pattern in (
        ("vegan", r"\bvegan\b"),
        ("vegetarian", r"\bvegetarian\b"),
        ("gluten-free", r"\bgluten[ -]?free\b"),
        ("halal", r"\bhalal\b"),
        ("kosher", r"\bkosher\b"),
    ):
        if re.search(pattern, text) and label not in found:
            found.append(label)
    allergy = re.search(r"\b([a-z]+)\s+allerg(?:y|ic)\b", text)
    if allergy:
        label = f"{allergy.group(1)} allergy"
        if label not in found:
            found.append(label)
    return found


def _price_level(text: str) -> int | None:
    if re.search(r"don'?t care about (?:the )?price|price doesn'?t matter|any price", text):
        return None
    if re.search(r"not too expensive|under \$?\d+", text):
        return 2
    if re.search(r"\bcheap\b|\bbudget\b|inexpensive|\baffordable\b|student budget|spend much", text):
        return 1
    if re.search(r"moderate|mid[- ]range", text):
        return 3
    if re.search(r"fine dining|splurge|very expensive|\bexpensive\b|upscale|\bfancy\b", text):
        return 4
    return None


def _vibe(text: str) -> str | None:
    word = "|".join(_VIBE_WORDS)
    match = re.search(rf"\b(?:somewhere|someplace)\s+({word})(?:\s+and\s+({word}))?\b", text)
    if match:
        if match.group(2):
            return f"{match.group(1)} and {match.group(2)}"
        return match.group(1)
    found = [item for item in _VIBE_WORDS if re.search(rf"\b{item}\b", text)]
    if not found:
        return None
    if len(found) == 1:
        return found[0]
    return f"{found[0]} and {found[1]}"


def _location_from_text(description: str) -> str | None:
    match = re.search(
        r"\b(?i:around|near|in|at)\s+([A-Z][A-Za-z0-9.'\-]*(?:\s+[A-Z][A-Za-z0-9.'\-]*){0,3})",
        description,
    )
    if match:
        return _clean_place(match.group(1))
    downtown = re.search(
        r"\b((?:Downtown|Uptown)(?:\s+[A-Z][A-Za-z0-9.'\-]*){1,3})\b",
        description,
    )
    if downtown:
        return _clean_place(downtown.group(1))
    return None


def _clean_place(value: str) -> str | None:
    place = re.split(r",|\.|(?:\s+\b(?:and|or|with|where|that|for|under|not|preferably)\b)", value, maxsplit=1)[0]
    place = " ".join(place.split()).strip(" -")
    if not place or place.lower() in {"somewhere", "something"}:
        return None
    return place[:80]


def _radius_meters(text: str) -> int | None:
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(kilometers|kilometres|km|miles|mile|mi|meters|meter|metres|metre|m)\b",
        text,
    )
    if match is None:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit in {"km", "kilometers", "kilometres"}:
        meters = amount * 1000
    elif unit in {"mi", "mile", "miles"}:
        meters = amount * 1609.344
    else:
        meters = amount
    rounded = int(round(meters))
    if 500 <= rounded <= 50000:
        return rounded
    return None
