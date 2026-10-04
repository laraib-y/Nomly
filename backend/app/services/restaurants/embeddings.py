"""Embedding providers.

Restaurant and query vectors share one dimension. The rest of Nomly asks an
EmbeddingProvider for a vector and does not know which model produced it.

Similarity metric: cosine similarity. Stored and query vectors use the same
length. A raw cosine in [-1, 1] is normalized to [0, 1] with (cosine + 1) / 2
before it is mixed with the structured score. TiDB's VEC_COSINE_DISTANCE is
1 - cosine similarity, so a distance of 0 is a similarity of 1.
"""

import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 768
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"


class EmbeddingError(Exception):
    """The embedding provider could not return a usable vector."""


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic bag-of-words vector for tests and local fallback."""

    def embed_text(self, text: str) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            raise EmbeddingError("Text is empty")
        vector = [0.0] * EMBEDDING_DIMENSION
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSION
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        return _l2_normalize(vector)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Production embeddings from the Gemini embed API. Not a generative reply."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_EMBEDDING_MODEL,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client = client

    def embed_text(self, text: str) -> list[float]:
        cleaned = " ".join(text.split())
        if not cleaned:
            raise EmbeddingError("Text is empty")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent"
        payload = {
            "content": {"parts": [{"text": cleaned}]},
            "outputDimensionality": EMBEDDING_DIMENSION,
        }
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=12.0)
        try:
            response = client.post(url, headers={"x-goog-api-key": self.api_key}, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Embedding request failed with status %s", exc.response.status_code)
            raise EmbeddingError("Embedding request failed") from None
        except httpx.HTTPError:
            logger.warning("Embedding request failed")
            raise EmbeddingError("Embedding request failed") from None
        finally:
            if owns_client:
                client.close()
        values = _embedding_values(body)
        if len(values) != EMBEDDING_DIMENSION:
            raise EmbeddingError("Unexpected embedding dimension")
        return [float(value) for value in values]


ProductionEmbeddingProvider = GeminiEmbeddingProvider


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.gemini_api_key.strip():
        return GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key.strip(),
            model=settings.embedding_model.strip() or DEFAULT_EMBEDDING_MODEL,
        )
    return MockEmbeddingProvider()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise EmbeddingError("Embedding dimensions do not match")
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def normalize_similarity(cosine: float) -> float:
    """Map cosine similarity from [-1, 1] onto [0, 1]."""

    clamped = max(-1.0, min(1.0, cosine))
    return (clamped + 1.0) / 2.0


def similarity_from_cosine_distance(distance: float) -> float:
    """TiDB VEC_COSINE_DISTANCE is 1 - cosine similarity."""

    return normalize_similarity(1.0 - distance)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        raise EmbeddingError("Text is empty")
    return [value / norm for value in vector]


def _embedding_values(body: object) -> list[float]:
    if not isinstance(body, dict):
        raise EmbeddingError("Embedding response was empty")
    embedding = body.get("embedding")
    if isinstance(embedding, dict) and isinstance(embedding.get("values"), list):
        return embedding["values"]
    embeddings = body.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, dict) and isinstance(first.get("values"), list):
            return first["values"]
    raise EmbeddingError("Embedding response did not include a vector")
