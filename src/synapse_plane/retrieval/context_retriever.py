"""Hybrid context retrieval: semantic search + explicit preferences +
entity-graph expansion, scored and trimmed to a token budget."""

from datetime import UTC, datetime

from synapse_plane.config import Settings
from synapse_plane.domain.memory import ContextItem, ContextPackage, Memory
from synapse_plane.memory.embedding_service import EmbeddingServiceProtocol
from synapse_plane.persistence.repositories import (
    EntityRepository,
    MemoryRepository,
)
from synapse_plane.retrieval.context_package_builder import ContextPackageBuilder

# weights must sum to 1.0 (stale_penalty is separate, subtractive)
_WEIGHT_SEMANTIC = 0.35
_WEIGHT_ENTITY = 0.20
_WEIGHT_CONFIDENCE = 0.20
_WEIGHT_RECENCY = 0.15
_WEIGHT_EXPLICIT = 0.10
_STALE_PENALTY = 0.30
_RECENCY_HORIZON_DAYS = 365


def _ensure_aware(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC (SQLite doesn't preserve tzinfo)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def score_memory(
    memory: Memory,
    *,
    semantic_similarity: float = 0.0,
    entity_match: bool = False,
    now: datetime | None = None,
) -> float:
    """Pure scoring function — no DB access, unit-testable directly."""
    now = now or datetime.now(UTC)
    observed_at = _ensure_aware(memory.observed_at)
    recency = max(0.0, 1 - (now - observed_at).days / _RECENCY_HORIZON_DAYS)
    explicit_boost = 1.0 if memory.explicit_or_inferred.value == "explicit" else 0.0
    is_stale = memory.valid_to is not None and _ensure_aware(memory.valid_to) < now

    score = (
        _WEIGHT_SEMANTIC * semantic_similarity
        + _WEIGHT_ENTITY * (1.0 if entity_match else 0.0)
        + _WEIGHT_CONFIDENCE * memory.confidence
        + _WEIGHT_RECENCY * recency
        + _WEIGHT_EXPLICIT * explicit_boost
    )
    return score - _STALE_PENALTY if is_stale else score


class HybridContextRetriever:
    def __init__(
        self,
        memory_repo: MemoryRepository,
        entity_repo: EntityRepository,
        embedding_service: EmbeddingServiceProtocol,
        settings: Settings,
    ):
        self.memory_repo = memory_repo
        self.entity_repo = entity_repo
        self.embedding_service = embedding_service
        self.settings = settings
        self.builder = ContextPackageBuilder()

    async def retrieve(self, intent: str, user_id: str) -> ContextPackage:
        intent_embedding = await self.embedding_service.embed(intent)

        semantic_hits = await self.memory_repo.search_by_embedding(
            user_id=user_id, query_embedding=intent_embedding, limit=20
        )
        distance_by_memory_id = {hit.memory.memory_id: hit.distance for hit in semantic_hits}

        explicit_prefs = await self.memory_repo.get_explicit_preferences(user_id)

        intent_entities = await self.entity_repo.find_mentioned(user_id, intent)
        graph_hits = await self.entity_repo.get_related_memories(
            user_id, [e.entity_id for e in intent_entities], max_depth=2
        )

        candidates: dict[str, Memory] = {}
        for memory in [h.memory for h in semantic_hits] + explicit_prefs + graph_hits:
            candidates[memory.memory_id] = memory

        entity_names = {e.canonical_name.replace("_", " ") for e in intent_entities} | {
            e.name.lower() for e in intent_entities
        }
        now = datetime.now(UTC)

        scored_items = [
            ContextItem(
                memory=memory,
                relevance_score=score_memory(
                    memory,
                    semantic_similarity=1 - distance_by_memory_id.get(memory.memory_id, 1.0),
                    entity_match=any(name in memory.content.lower() for name in entity_names),
                    now=now,
                ),
                retrieval_reason=self._explain_reason(memory, distance_by_memory_id, graph_hits),
            )
            for memory in candidates.values()
        ]

        return self.builder.build(
            scored_items,
            intent=intent,
            total_memories_scanned=len(candidates),
            token_budget=self.settings.context_token_budget,
            max_items=self.settings.max_context_items,
        )

    @staticmethod
    def _explain_reason(
        memory: Memory, distance_by_memory_id: dict[str, float], graph_hits: list[Memory]
    ) -> str:
        if memory.memory_id in distance_by_memory_id:
            return "semantic_similarity"
        if any(m.memory_id == memory.memory_id for m in graph_hits):
            return "entity_graph"
        return "explicit_preference"
