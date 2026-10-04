import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.models import Base, Restaurant
from app.services.restaurants.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingError,
    GeminiEmbeddingProvider,
    MockEmbeddingProvider,
    ProductionEmbeddingProvider,
    get_embedding_provider,
)
from app.services.restaurants.refresh_embeddings import refresh_embeddings
from app.services.restaurants.semantic_text import sync_semantic_source


def test_mock_embeddings_are_deterministic_and_the_right_length():
    provider = MockEmbeddingProvider()
    first = provider.embed_text("cozy and quiet")
    second = provider.embed_text("  Cozy and quiet ")
    other = provider.embed_text("lively nightclub")

    assert len(first) == EMBEDDING_DIMENSION
    assert first == second
    assert first != other
    assert abs(sum(value * value for value in first) - 1) < 1e-6


def test_empty_text_is_rejected():
    with pytest.raises(EmbeddingError):
        MockEmbeddingProvider().embed_text("   ")


def test_blank_key_uses_the_mock_provider():
    settings = Settings(gemini_api_key="", database_url="sqlite://")
    assert isinstance(get_embedding_provider(settings), MockEmbeddingProvider)


def test_configured_key_uses_the_production_provider_without_calling_it():
    settings = Settings(gemini_api_key="server-side-key", embedding_model="text-embedding-004", database_url="sqlite://")
    provider = get_embedding_provider(settings)
    assert isinstance(provider, GeminiEmbeddingProvider)
    assert isinstance(provider, ProductionEmbeddingProvider)
    assert provider.api_key == "server-side-key"


def test_provider_failure_hides_the_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "secret-key"
        assert "secret-key" not in str(request.url)
        return httpx.Response(503, json={"error": "unavailable"})

    provider = GeminiEmbeddingProvider(
        "secret-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(EmbeddingError) as exc:
        provider.embed_text("cozy")
    assert "secret-key" not in str(exc.value)


def test_empty_production_text_does_not_call_the_network():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("empty text should not be sent")

    provider = GeminiEmbeddingProvider(
        "secret-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(EmbeddingError):
        provider.embed_text(" ")


def test_unexpected_dimension_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embedding": {"values": [0.1, 0.2]}})

    provider = GeminiEmbeddingProvider(
        "secret-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(EmbeddingError) as exc:
        provider.embed_text("cozy")
    assert "secret-key" not in str(exc.value)


def test_refresh_skips_unchanged_embeddings_and_regenerates_stale_ones():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    restaurant = Restaurant(external_id="han", name="Han River BBQ", cuisine="Korean", price=2, rating=4.7, source="mock")
    db.add(restaurant)
    db.commit()

    class CountingEmbedder(MockEmbeddingProvider):
        def __init__(self) -> None:
            self.calls = 0

        def embed_text(self, text: str) -> list[float]:
            self.calls += 1
            return super().embed_text(text)

    embedder = CountingEmbedder()
    first = refresh_embeddings(db, embedder)
    assert first.updated == 1
    assert first.failed == 0
    assert embedder.calls == 1
    stored = json.loads(restaurant.embedding_json)
    assert len(stored) == EMBEDDING_DIMENSION

    second = refresh_embeddings(db, embedder)
    assert second.updated == 0
    assert second.skipped == 1
    assert embedder.calls == 1

    restaurant.description = "Tabletop grills"
    assert sync_semantic_source(restaurant, restaurant) is True
    db.commit()
    third = refresh_embeddings(db, embedder)
    assert third.updated == 1
    assert embedder.calls == 2
    db.close()
