"""Writes execution outcomes back into memory — the feedback loop."""

from datetime import UTC, datetime
from uuid import uuid4

from synapse_plane.domain.enums import ExplicitOrInferred, MemoryType
from synapse_plane.domain.memory import Memory
from synapse_plane.memory.embedding_service import EmbeddingServiceProtocol
from synapse_plane.persistence.repositories import MemoryRepository


# Records what happened after an execution completes — one operation, no reasoning
class MemoryStoreTool:
    def __init__(self, memory_repo: MemoryRepository, embedding_service: EmbeddingServiceProtocol):
        self.memory_repo = memory_repo
        self.embedding_service = embedding_service

    async def record_outcome(self, user_id: str, content: str) -> Memory:
        now = datetime.now(UTC)
        memory = Memory(
            memory_id=str(uuid4()),
            user_id=user_id,
            memory_type=MemoryType.OUTCOME,
            content=content,
            confidence=0.9,
            explicit_or_inferred=ExplicitOrInferred.EXPLICIT,
            valid_from=now,
            source="action_outcome",
            created_at=now,
            observed_at=now,
        )
        await self.memory_repo.create(memory)
        embedding = await self.embedding_service.embed(content)
        await self.memory_repo.store_embedding(
            memory.memory_id, embedding, self.embedding_service.model
        )
        return memory
