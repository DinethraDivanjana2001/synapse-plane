"""Embedding generation — real (OpenAI) and fake (deterministic, tests/demo)."""

import hashlib
import random
from typing import Protocol

# gemini-embedding-001's real output size (verified with a real call) — the
# fake embedding must match, since both write into the same fixed-width
# pgvector column.
EMBEDDING_DIMENSIONS = 3072


# Interface any embedding service (real or fake) must implement
class EmbeddingServiceProtocol(Protocol):
    model: str

    async def embed(self, text: str) -> list[float]: ...


class EmbeddingService:
    """Real embedding calls via an OpenAI-compatible client — Gemini's
    endpoint in this project, verified to serve gemini-embedding-001."""

    def __init__(self, client: object, model: str = "gemini-embedding-001"):
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
