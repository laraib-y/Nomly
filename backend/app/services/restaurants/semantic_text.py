"""Grounded text for restaurant embeddings.

The text uses only fields already stored on the restaurant. It does not add
atmosphere, noise, or dietary claims that the source data does not contain.
"""

import hashlib
import json


def build_restaurant_semantic_text(restaurant: object) -> str:
    parts: list[str] = []
    name = _clean(getattr(restaurant, "name", None))
    if name:
        parts.append(name)
    cuisine = _clean(getattr(restaurant, "cuisine", None))
    if cuisine:
        parts.append(f"Cuisine {cuisine}")
    price = getattr(restaurant, "price", None)
    if isinstance(price, int):
        parts.append(f"Price level {price}")
    rating = getattr(restaurant, "rating", None)
    if isinstance(rating, (int, float)) and not isinstance(rating, bool):
        parts.append(f"Rating {rating}")
    address = _clean(getattr(restaurant, "address", None))
    if address:
        parts.append(f"Address {address}")
    categories = _categories(getattr(restaurant, "categories", None))
    if categories:
        parts.append("Categories " + ", ".join(categories))
    description = _clean(getattr(restaurant, "description", None))
    if description:
        parts.append(description)
    return ". ".join(parts)


def semantic_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sync_semantic_source(restaurant: object, source: object) -> bool:
    """Store grounded text. Clear a stored embedding when that text changes."""

    text = build_restaurant_semantic_text(source)
    digest = semantic_text_hash(text)
    if getattr(restaurant, "semantic_text_hash", None) == digest:
        return False
    restaurant.semantic_text = text
    restaurant.semantic_text_hash = digest
    restaurant.embedding_json = None
    return True


def _clean(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _categories(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [_clean(stripped)] if _clean(stripped) else []
        value = parsed
    if not isinstance(value, (list, tuple)):
        return []
    cleaned = [_clean(item) for item in value]
    return [item for item in cleaned if item]
