"""Embedding helpers for semantic news search and RAG (Phase 3)."""

from __future__ import annotations

import math
from typing import Any, List, Sequence

from backend.core.venice_api_client import VeniceAPIClient


class EmbeddingError(RuntimeError):
    """Raised when the embeddings endpoint cannot be used."""


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity with zero-vector protection."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _extract_embeddings(payload: Any) -> List[List[float]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise EmbeddingError("Unexpected embeddings payload")
    vectors: List[List[float]] = []
    for item in data:
        embedding = item.get("embedding") if isinstance(item, dict) else None
        if not isinstance(embedding, list):
            raise EmbeddingError("Embeddings payload item is missing 'embedding'")
        vectors.append([float(value) for value in embedding])
    return vectors


async def embed_texts(
    client: VeniceAPIClient,
    model: str,
    texts: Sequence[str],
) -> List[List[float]]:
    """Embed a batch of texts. Keep batches small (news articles + query)."""
    if not texts:
        return []
    payload = {"model": model, "input": list(texts)}
    response = await client.post_json("/embeddings", data=payload, timeout=60.0)
    return _extract_embeddings(response)


async def rank_by_similarity(
    client: VeniceAPIClient,
    model: str,
    query: str,
    documents: Sequence[str],
    *,
    top_k: int = 5,
) -> List[tuple[int, float]]:
    """Return ``(index, score)`` tuples sorted by descending similarity."""
    if not documents:
        return []
    vectors = await embed_texts(client, model, [query, *documents])
    if len(vectors) != len(documents) + 1:
        raise EmbeddingError("Embeddings count does not match inputs")
    query_vector = vectors[0]
    scored = [
        (index, cosine_similarity(query_vector, vector))
        for index, vector in enumerate(vectors[1:])
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[: max(1, top_k)]
