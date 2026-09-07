"""Domain models for persistent memory, entities, relationships, and retrieved context."""

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


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str
    role: str = "subject"


class ExtractedRelationship(BaseModel):
    source: str
    relationship_type: str
    target: str


class MemoryExtractionResult(BaseModel):
    """LLM extraction output — a proposal, not authoritative."""

    memory_type: MemoryType
    confidence: float = Field(ge=0.0, le=1.0)
    explicit_or_inferred: ExplicitOrInferred
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


class ContextPackage(BaseModel):
    items: list[ContextItem]
    intent: str
    retrieved_at: datetime
    total_memories_scanned: int
    token_estimate: int

    @property
    def provenance(self) -> list[str]:
        """Source trail for each retained item, for UI display."""
        return [f"{item.memory.memory_type.value}:{item.memory.source}" for item in self.items]
