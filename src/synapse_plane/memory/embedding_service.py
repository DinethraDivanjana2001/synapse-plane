"""Embedding generation — real (OpenAI) and fake (deterministic, tests/demo)."""

import hashlib
import random
from typing import Protocol

EMBEDDING_DIMENSIONS = 1536


class EmbeddingServiceProtocol(Protocol):
    model: str

    async def embed(self, text: str) -> list[float]: ...


class EmbeddingService:
    """Real OpenAI-backed implementation."""

    def __init__(self, client: object, model: str = "text-embedding-3-small"):
        self.client = client
        self.model = model

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        response = await self.client.embeddings.create(input=text, model=self.model)  # type: ignore[attr-defined]
        return list(response.data[0].embedding)


class FakeEmbeddingService:
    """Deterministic hash-seeded fake vector — no network calls."""

    model = "fake-embedding-v1"

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return [rng.gauss(0, 1) for _ in range(EMBEDDING_DIMENSIONS)]
