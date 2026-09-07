"""Integration tests for memory ingestion and hybrid retrieval.
Real DB (in-memory SQLite), Fake extractor/embeddings — no external I/O.
"""

from synapse_plane.config import Settings
from synapse_plane.memory.embedding_service import FakeEmbeddingService
from synapse_plane.memory.ingestion import FakeMemoryExtractor, MemoryIngestionPipeline
from synapse_plane.persistence.repositories import EntityRepository, MemoryRepository
from synapse_plane.retrieval.context_retriever import HybridContextRetriever

USER_ID = "user-1"

# A mix of relevant (restaurant/Maya/dinner) and irrelevant notes — the
# retriever must tell them apart, not just return everything.
RELEVANT_NOTES = [
    "I prefer quiet restaurants over lively, noisy ones",
    "Maya is my colleague and she loves Italian food",
    "Last visit to Bella Roma was too loud for dinner conversation",
    "Usually free for dinner after 7pm on weekdays",
    "Chose a quiet Italian restaurant for dinner with Maya last time",
]
IRRELEVANT_NOTES = [
    "I prefer morning gym sessions over evening ones",
    "Learning Spanish, targeting B1 level by March",
    "I like using mechanical keyboards, currently a Keychron K2",
    "Attended a React conference last Thursday",
    "Want to finish reading 12 books this year",
    "Considering switching from a MacBook to a Linux laptop",
    "Went for a 10km run on Sunday morning",
    "Saving up for a new camera lens by year end",
    "Fixed a flaky CI pipeline at work today",
    "My sister is a doctor in another city",
    "Watched a documentary about deep-sea exploration",
    "Trying to drink more water during the day",
]

_KEYWORDS = [
    "restaurant",
    "quiet",
    "maya",
    "dinner",
    "italian",
    "gym",
    "spanish",
    "keyboard",
    "conference",
    "book",
]


class KeywordEmbeddingService:
    """Deterministic bag-of-keywords 'embedding' — unlike FakeEmbeddingService
    (random hash-seeded, used elsewhere), this one gives meaningful cosine
    similarity so semantic-search assertions here aren't flaky. Test-only;
    never used in application code."""

    model = "keyword-fake-v1"

    async def embed(self, text: str) -> list[float]:
        lowered = text.lower()
        return [float(lowered.count(k)) for k in _KEYWORDS]


def make_pipeline(db_session) -> MemoryIngestionPipeline:
    return MemoryIngestionPipeline(
        extractor=FakeMemoryExtractor(),
        embedding_service=FakeEmbeddingService(),
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
    )


async def test_ingest_creates_memory_and_embedding(db_session) -> None:
    pipeline = make_pipeline(db_session)

    memory = await pipeline.ingest(USER_ID, "I prefer quiet restaurants", source="user_input")
    await db_session.commit()

    stored = await MemoryRepository(db_session).list_by_user(USER_ID)
    assert len(stored) == 1
    assert stored[0].memory_id == memory.memory_id
    assert stored[0].content == "I prefer quiet restaurants"


async def test_ingest_extracts_entities(db_session) -> None:
    pipeline = make_pipeline(db_session)

    await pipeline.ingest(
        USER_ID, "Maya is my colleague from the product team", source="user_input"
    )
    await db_session.commit()

    entities = await EntityRepository(db_session).find_mentioned(USER_ID, "Maya")
    assert any(e.canonical_name == "maya" for e in entities)


async def _seed_mixed_notes(db_session) -> MemoryIngestionPipeline:
    pipeline = MemoryIngestionPipeline(
        extractor=FakeMemoryExtractor(),
        embedding_service=KeywordEmbeddingService(),
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
    )
    for note in RELEVANT_NOTES + IRRELEVANT_NOTES:
        await pipeline.ingest(USER_ID, note, source="user_input")
    await db_session.commit()
    return pipeline


async def test_retrieval_returns_relevant_subset_from_large_seed(db_session) -> None:
    await _seed_mixed_notes(db_session)
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:", max_context_items=len(RELEVANT_NOTES)
    )
    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
        embedding_service=KeywordEmbeddingService(),
        settings=settings,
    )

    package = await retriever.retrieve("Find a good restaurant for dinner with Maya", USER_ID)

    assert package.total_memories_scanned == len(RELEVANT_NOTES) + len(IRRELEVANT_NOTES)
    assert 0 < len(package.items) < package.total_memories_scanned
    assert len(package.items) <= settings.max_context_items


async def test_retrieval_excludes_irrelevant_memories(db_session) -> None:
    await _seed_mixed_notes(db_session)
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:", max_context_items=len(RELEVANT_NOTES)
    )
    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
        embedding_service=KeywordEmbeddingService(),
        settings=settings,
    )

    package = await retriever.retrieve("Find a good restaurant for dinner with Maya", USER_ID)

    returned_content = {item.memory.content for item in package.items}
    assert returned_content == set(RELEVANT_NOTES)
    for irrelevant in IRRELEVANT_NOTES:
        assert irrelevant not in returned_content
    assert "I like using mechanical keyboards, currently a Keychron K2" not in returned_content
    assert any("restaurant" in c.lower() or "maya" in c.lower() for c in returned_content)
