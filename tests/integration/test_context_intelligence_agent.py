"""Integration tests for ContextIntelligenceAgent — needs a DB, so lives here
rather than tests/unit (project convention: unit tests never touch a DB)."""

from datetime import UTC, datetime
from uuid import uuid4

from synapse_plane.agents.base import AgentInput
from synapse_plane.agents.internal.context_intelligence import ContextIntelligenceAgent
from synapse_plane.config import Settings
from synapse_plane.domain.enums import ExplicitOrInferred, MemoryType
from synapse_plane.domain.memory import Memory
from synapse_plane.memory.embedding_service import FakeEmbeddingService
from synapse_plane.persistence.repositories import EntityRepository, MemoryRepository
from synapse_plane.retrieval.context_retriever import HybridContextRetriever

USER_ID = "user-1"


async def _seed_memory(db_session, content: str) -> None:
    now = datetime.now(UTC)
    repo = MemoryRepository(db_session)
    memory = Memory(
        memory_id=str(uuid4()),
        user_id=USER_ID,
        memory_type=MemoryType.PREFERENCE,
        content=content,
        confidence=0.9,
        explicit_or_inferred=ExplicitOrInferred.EXPLICIT,
        valid_from=now,
        source="user_input",
        created_at=now,
        observed_at=now,
    )
    await repo.create(memory)
    embeddings = FakeEmbeddingService()
    vector = await embeddings.embed(content)
    await repo.store_embedding(memory.memory_id, vector, embeddings.model)


async def test_agent_returns_context_package_with_provenance(db_session) -> None:
    await _seed_memory(db_session, "I prefer quiet restaurants")
    await db_session.commit()

    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
        embedding_service=FakeEmbeddingService(),
        settings=Settings(database_url="sqlite+aiosqlite:///:memory:"),
    )
    agent = ContextIntelligenceAgent(retriever)

    output = await agent.execute(
        AgentInput(
            goal="Find a quiet restaurant",
            task_id="t1",
            execution_id="e1",
            context={"user_id": USER_ID},
        )
    )

    assert output.success is True
    assert output.agent_id == "internal-context-intelligence"
    assert output.result["total_memories_scanned"] == 1
    assert len(output.result["items"]) == 1


async def test_agent_health_check_is_true(db_session) -> None:
    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
        embedding_service=FakeEmbeddingService(),
        settings=Settings(database_url="sqlite+aiosqlite:///:memory:"),
    )
    assert ContextIntelligenceAgent(retriever).health_check() is True
