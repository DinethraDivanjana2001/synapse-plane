"""Repository classes — the only code allowed to touch ORM models directly.
Everything above this layer speaks Pydantic domain models (docs/AGENTS.md
layer rules: Persistence stores/loads state, no business logic).
"""

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import ExplicitOrInferred, MemoryType
from synapse_plane.domain.memory import Entity, Memory
from synapse_plane.domain.profile import UserProfile
from synapse_plane.persistence.models import (
    AgentManifestModel,
    ContextRetrievalModel,
    EntityModel,
    MemoryEmbeddingModel,
    MemoryEntityModel,
    MemoryModel,
    RelationshipModel,
    UserProfileModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class MemorySearchHit:
    memory: Memory
    distance: float


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Pure-Python fallback for the SQLite test path — Postgres uses the real
    pgvector `<=>` operator instead (see MemoryRepository.search_by_embedding)."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - dot / (norm_a * norm_b)


def _memory_from_row(row: MemoryModel) -> Memory:
    return Memory(
        memory_id=row.id,
        user_id=row.user_id,
        memory_type=MemoryType(row.memory_type),
        content=row.content,
        confidence=row.confidence,
        explicit_or_inferred=ExplicitOrInferred(row.explicit_or_inferred),
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        supersedes_fact_id=row.supersedes_fact_id,
        source=row.source,
        created_at=row.created_at,
        observed_at=row.observed_at,
    )


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, memory: Memory) -> Memory:
        row = MemoryModel(
            id=memory.memory_id,
            user_id=memory.user_id,
            memory_type=memory.memory_type.value,
            content=memory.content,
            confidence=memory.confidence,
            explicit_or_inferred=memory.explicit_or_inferred.value,
            valid_from=memory.valid_from,
            valid_to=memory.valid_to,
            supersedes_fact_id=memory.supersedes_fact_id,
            source=memory.source,
            created_at=memory.created_at,
            observed_at=memory.observed_at,
        )
        self.session.add(row)
        await self.session.flush()
        return memory

    async def store_embedding(self, memory_id: str, embedding: list[float], model: str) -> None:
        self.session.add(
            MemoryEmbeddingModel(
                id=str(uuid4()),
                memory_id=memory_id,
                embedding=embedding,
                model_name=model,
                created_at=_now(),
            )
        )
        await self.session.flush()

    async def list_by_user(self, user_id: str) -> list[Memory]:
        result = await self.session.execute(
            select(MemoryModel).where(MemoryModel.user_id == user_id)
        )
        return [_memory_from_row(row) for row in result.scalars().all()]

    async def get_explicit_preferences(self, user_id: str) -> list[Memory]:
        result = await self.session.execute(
            select(MemoryModel).where(
                MemoryModel.user_id == user_id,
                MemoryModel.memory_type == MemoryType.PREFERENCE.value,
                MemoryModel.explicit_or_inferred == ExplicitOrInferred.EXPLICIT.value,
                MemoryModel.valid_to.is_(None),
            )
        )
        return [_memory_from_row(row) for row in result.scalars().all()]

    async def update_type_and_confidence(
        self, memory_id: str, memory_type: MemoryType, confidence: float
    ) -> None:
        row = await self.session.get(MemoryModel, memory_id)
        if row is not None:
            row.memory_type = memory_type.value
            row.confidence = confidence
            await self.session.flush()

    async def search_by_embedding(
        self, user_id: str, query_embedding: list[float], limit: int
    ) -> list[MemorySearchHit]:
        """Nearest-neighbour search over currently-valid memories.

        Postgres: real pgvector cosine distance (`<=>`), computed in the
        database. SQLite (tests only, no pgvector extension): fetch the
        candidate set and compute cosine distance in Python — correct but
        O(n), fine at seed-data scale, never used in production.
        """
        dialect = self.session.bind.dialect.name if self.session.bind else "postgresql"
        if dialect == "postgresql":
            result = await self.session.execute(
                text(
                    """
                    SELECT m.id, (e.embedding <=> CAST(:query_vec AS vector)) AS distance
                    FROM memory_embeddings e
                    JOIN memories m ON e.memory_id = m.id
                    WHERE m.user_id = :user_id AND m.valid_to IS NULL
                    ORDER BY distance ASC
                    LIMIT :limit
                    """
                ),
                {"query_vec": str(query_embedding), "user_id": user_id, "limit": limit},
            )
            rows = result.all()
            memories_by_id = {m.memory_id: m for m in await self.list_by_user(user_id)}
            return [
                MemorySearchHit(memory=memories_by_id[row.id], distance=row.distance)
                for row in rows
                if row.id in memories_by_id
            ]

        # SQLite fallback: brute-force in Python.
        result = await self.session.execute(
            select(MemoryModel, MemoryEmbeddingModel.embedding)
            .join(MemoryEmbeddingModel, MemoryEmbeddingModel.memory_id == MemoryModel.id)
            .where(MemoryModel.user_id == user_id, MemoryModel.valid_to.is_(None))
        )
        hits = [
            MemorySearchHit(
                memory=_memory_from_row(row), distance=_cosine_distance(embedding, query_embedding)
            )
            for row, embedding in result.all()
        ]
        hits.sort(key=lambda h: h.distance)
        return hits[:limit]


class EntityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self, user_id: str, entity_type: str, name: str, canonical_name: str
    ) -> Entity:
        result = await self.session.execute(
            select(EntityModel).where(
                EntityModel.user_id == user_id, EntityModel.canonical_name == canonical_name
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = EntityModel(
                id=str(uuid4()),
                user_id=user_id,
                entity_type=entity_type,
                name=name,
                canonical_name=canonical_name,
                metadata_json="{}",
                created_at=_now(),
            )
            self.session.add(row)
            await self.session.flush()
        return Entity(
            entity_id=row.id,
            user_id=row.user_id,
            entity_type=row.entity_type,  # type: ignore[arg-type]
            name=row.name,
            canonical_name=row.canonical_name,
            metadata=json.loads(row.metadata_json),
            created_at=row.created_at,
        )

    async def link_to_memory(self, entity_id: str, memory_id: str, role: str) -> None:
        self.session.add(
            MemoryEntityModel(id=str(uuid4()), memory_id=memory_id, entity_id=entity_id, role=role)
        )
        await self.session.flush()

    async def find_mentioned(self, user_id: str, text_: str) -> list[Entity]:
        """Deterministic substring match against the user's own entity
        catalogue. Good enough for the retriever's entity-graph expansion;
        deeper NLU belongs to the Context Intelligence Agent (Step 4), not
        this repository layer."""
        result = await self.session.execute(
            select(EntityModel).where(EntityModel.user_id == user_id)
        )
        haystack = text_.lower()
        return [
            Entity(
                entity_id=row.id,
                user_id=row.user_id,
                entity_type=row.entity_type,  # type: ignore[arg-type]
                name=row.name,
                canonical_name=row.canonical_name,
                metadata=json.loads(row.metadata_json),
                created_at=row.created_at,
            )
            for row in result.scalars().all()
            if row.canonical_name.replace("_", " ") in haystack or row.name.lower() in haystack
        ]

    async def get_related_memories(
        self, user_id: str, entity_ids: list[str], max_depth: int = 2
    ) -> list[Memory]:
        """BFS over `relationships` up to max_depth hops from entity_ids,
        then every memory linked to any entity reached."""
        if not entity_ids:
            return []

        frontier = set(entity_ids)
        visited = set(entity_ids)
        for _ in range(max_depth):
            if not frontier:
                break
            result = await self.session.execute(
                select(
                    RelationshipModel.source_entity_id, RelationshipModel.target_entity_id
                ).where(
                    RelationshipModel.user_id == user_id,
                    (RelationshipModel.source_entity_id.in_(frontier))
                    | (RelationshipModel.target_entity_id.in_(frontier)),
                )
            )
            next_frontier = set()
            for source_id, target_id in result.all():
                for candidate in (source_id, target_id):
                    if candidate not in visited:
                        visited.add(candidate)
                        next_frontier.add(candidate)
            frontier = next_frontier

        result = await self.session.execute(
            select(MemoryModel)
            .join(MemoryEntityModel, MemoryEntityModel.memory_id == MemoryModel.id)
            .where(MemoryEntityModel.entity_id.in_(visited), MemoryModel.valid_to.is_(None))
        )
        return [_memory_from_row(row) for row in result.scalars().unique().all()]


class ContextRetrievalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        execution_id: str,
        intent: str,
        context_package_json: str,
        memories_scanned: int,
        items_returned: int,
        token_estimate: int,
    ) -> str:
        retrieval_id = str(uuid4())
        self.session.add(
            ContextRetrievalModel(
                id=retrieval_id,
                execution_id=execution_id,
                intent=intent,
                context_package_json=context_package_json,
                memories_scanned=memories_scanned,
                items_returned=items_returned,
                token_estimate=token_estimate,
                retrieved_at=_now(),
            )
        )
        await self.session.flush()
        return retrieval_id


class AgentManifestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, manifest: AgentManifest) -> None:
        existing = await self.session.get(AgentManifestModel, manifest.agent_id)
        if existing is not None:
            await self.session.delete(existing)
            await self.session.flush()
        self.session.add(
            AgentManifestModel(
                id=manifest.agent_id,
                name=manifest.name,
                ownership=manifest.ownership.value,
                source_repository=manifest.source_repository,
                version=manifest.version,
                description=manifest.description,
                capabilities_json=json.dumps(manifest.capabilities),
                endpoint=manifest.endpoint,
                protocol=manifest.protocol,
                input_schema=manifest.input_schema,
                output_schema=manifest.output_schema,
                permissions_json=json.dumps(manifest.permissions),
                side_effect_level=manifest.side_effect_level.value,
                trust_status=manifest.trust_status.value,
                enabled=manifest.enabled,
                health_status=manifest.health_status.value,
                implementation_status=manifest.implementation_status.value,
                reliability_score=manifest.reliability_score,
                estimated_latency_ms=manifest.estimated_latency_ms,
                estimated_cost_units=manifest.estimated_cost_units,
                timeout_seconds=manifest.timeout_seconds,
                max_concurrency=manifest.max_concurrency,
                tags_json=json.dumps(manifest.tags),
            )
        )
        await self.session.flush()

    async def list_all(self) -> list[AgentManifest]:
        result = await self.session.execute(select(AgentManifestModel))
        return [_manifest_from_row(row) for row in result.scalars().all()]


def _manifest_from_row(row: AgentManifestModel) -> AgentManifest:
    return AgentManifest(
        agent_id=row.id,
        name=row.name,
        ownership=row.ownership,  # type: ignore[arg-type]
        source_repository=row.source_repository,
        version=row.version,
        description=row.description,
        capabilities=json.loads(row.capabilities_json),
        endpoint=row.endpoint,
        protocol=row.protocol,
        input_schema=row.input_schema,
        output_schema=row.output_schema,
        permissions=json.loads(row.permissions_json),
        side_effect_level=row.side_effect_level,  # type: ignore[arg-type]
        trust_status=row.trust_status,  # type: ignore[arg-type]
        enabled=row.enabled,
        health_status=row.health_status,  # type: ignore[arg-type]
        implementation_status=row.implementation_status,  # type: ignore[arg-type]
        reliability_score=row.reliability_score,
        estimated_latency_ms=row.estimated_latency_ms,
        estimated_cost_units=row.estimated_cost_units,
        timeout_seconds=row.timeout_seconds,
        max_concurrency=row.max_concurrency,
        tags=json.loads(row.tags_json),
    )


class UserProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, profile: UserProfile) -> None:
        existing = await self.session.get(UserProfileModel, profile.user_id)
        now = _now()
        if existing is not None:
            existing.display_name = profile.display_name
            existing.profile_json = profile.model_dump_json()
            existing.updated_at = now
        else:
            self.session.add(
                UserProfileModel(
                    id=profile.user_id,
                    display_name=profile.display_name,
                    profile_json=profile.model_dump_json(),
                    created_at=now,
                    updated_at=now,
                )
            )
        await self.session.flush()

    async def get(self, user_id: str) -> UserProfile | None:
        row = await self.session.get(UserProfileModel, user_id)
        if row is None:
            return None
        return UserProfile.model_validate_json(row.profile_json)
