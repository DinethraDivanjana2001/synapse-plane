"""Domain models for persistent memory, entities, relationships, and
retrieved context. See docs/MEMORY_AND_RAG.md for the design rationale.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from synapse_plane.domain.enums import EntityType, ExplicitOrInferred, MemoryType


class Memory(BaseModel):
    memory_id: str
    user_id: str
    memory_type: MemoryType
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    explicit_or_inferred: ExplicitOrInferred
    valid_from: datetime
    valid_to: datetime | None = None
    supersedes_fact_id: str | None = None
    source: str
    created_at: datetime
    observed_at: datetime

    @property
    def is_currently_valid(self) -> bool:
        return self.valid_to is None


class Entity(BaseModel):
    entity_id: str
    user_id: str
    entity_type: EntityType
    name: str
    canonical_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class Relationship(BaseModel):
    relationship_id: str
    user_id: str
    source_entity_id: str
    relationship_type: str
    target_entity_id: str
    weight: float = 1.0
    valid_from: datetime
    valid_to: datetime | None = None
    source_memory_id: str | None = None


class ContextItem(BaseModel):
    memory: Memory
    relevance_score: float
    retrieval_reason: str


class ContextPackage(BaseModel):
    items: list[ContextItem]
    intent: str
    retrieved_at: datetime
    total_memories_scanned: int
    token_estimate: int

    @property
    def provenance(self) -> list[str]:
        """Human-readable source trail for every retained item — what the UI's
        'Retrieved Context' panel renders (docs/MEMORY_AND_RAG.md)."""
        return [f"{item.memory.memory_type.value}:{item.memory.source}" for item in self.items]
