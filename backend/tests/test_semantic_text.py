from types import SimpleNamespace

from app.services.restaurants.semantic_text import (
    build_restaurant_semantic_text,
    semantic_text_hash,
    sync_semantic_source,
)


def _restaurant(**overrides):
    values = {
        "name": "Han River BBQ",
        "cuisine": "Korean",
        "price": 2,
        "rating": 4.7,
        "address": "Burnaby, BC",
        "categories": ["Korean", "Barbecue"],
        "description": "Korean BBQ restaurant",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_semantic_text_includes_known_fields_only():
    text = build_restaurant_semantic_text(_restaurant())

    assert "Han River BBQ" in text
    assert "Cuisine Korean" in text
    assert "Price level 2" in text
    assert "Rating 4.7" in text
    assert "Address Burnaby, BC" in text
    assert "Categories Korean, Barbecue" in text
    assert "Korean BBQ restaurant" in text
    lowered = text.lower()
    assert "cozy" not in lowered
    assert "romantic" not in lowered
    assert "quiet" not in lowered
    assert "family-friendly" not in lowered


def test_semantic_text_is_deterministic():
    restaurant = _restaurant()
    assert build_restaurant_semantic_text(restaurant) == build_restaurant_semantic_text(restaurant)


def test_missing_optional_fields_do_not_crash():
    text = build_restaurant_semantic_text(
        _restaurant(
            cuisine=None,
            price=None,
            rating=None,
            address=None,
            categories=None,
            description=None,
        )
    )
    assert text == "Han River BBQ"


def test_json_categories_are_read_from_stored_rows():
    text = build_restaurant_semantic_text(_restaurant(categories='["Korean", "Barbecue"]'))
    assert "Categories Korean, Barbecue" in text


def test_changed_text_clears_the_stored_embedding():
    restaurant = SimpleNamespace(semantic_text=None, semantic_text_hash=None, embedding_json="[1]")
    source = _restaurant()

    assert sync_semantic_source(restaurant, source) is True
    assert restaurant.embedding_json is None
    digest = restaurant.semantic_text_hash
    assert digest == semantic_text_hash(restaurant.semantic_text)

    assert sync_semantic_source(restaurant, source) is False
    restaurant.embedding_json = "[1]"
    source.description = "A different menu"
    assert sync_semantic_source(restaurant, source) is True
    assert restaurant.embedding_json is None
    assert restaurant.semantic_text_hash != digest
