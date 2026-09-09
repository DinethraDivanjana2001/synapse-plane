"""Integration tests for the persistence layer and demo seed data shape."""

from datetime import UTC, datetime
from uuid import uuid4

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import (
    AgentHealthStatus,
    AgentImplementationStatus,
    AgentOwnership,
    AgentTrustStatus,
    EntityType,
    ExplicitOrInferred,
    MemoryType,
    SideEffectLevel,
)
from synapse_plane.domain.memory import Memory
from synapse_plane.domain.profile import (
    ApprovalPolicyConfig,
    CalendarConfig,
    FoodPreferences,
    Location,
    TravelPreferences,
    UserProfile,
)
from synapse_plane.memory.embedding_service import FakeEmbeddingService
from synapse_plane.persistence.repositories import (
    AgentManifestRepository,
    EntityRepository,
    MemoryRepository,
    UserProfileRepository,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def test_memory_create_and_store_embedding_roundtrip(db_session) -> None:
    repo = MemoryRepository(db_session)
    embeddings = FakeEmbeddingService()

    memory = Memory(
        memory_id=str(uuid4()),
        user_id="user-1",
        memory_type=MemoryType.PREFERENCE,
        content="I prefer quiet restaurants",
        confidence=0.9,
        explicit_or_inferred=ExplicitOrInferred.EXPLICIT,
        valid_from=_now(),
        source="user_input",
        created_at=_now(),
        observed_at=_now(),
    )
    await repo.create(memory)
    vector = await embeddings.embed(memory.content)
    await repo.store_embedding(memory.memory_id, vector, embeddings.model)
    await db_session.commit()

    stored = await repo.list_by_user("user-1")
    assert len(stored) == 1
    assert stored[0].content == "I prefer quiet restaurants"


async def test_get_explicit_preferences_excludes_inferred(db_session) -> None:
    repo = MemoryRepository(db_session)
    explicit = Memory(
        memory_id=str(uuid4()),
        user_id="user-1",
        memory_type=MemoryType.PREFERENCE,
        content="explicit pref",
        confidence=0.9,
        explicit_or_inferred=ExplicitOrInferred.EXPLICIT,
        valid_from=_now(),
        source="user_input",
        created_at=_now(),
        observed_at=_now(),
    )
    inferred = explicit.model_copy(
        update={
            "memory_id": str(uuid4()),
            "content": "inferred pref",
            "explicit_or_inferred": ExplicitOrInferred.INFERRED,
        }
    )
    await repo.create(explicit)
    await repo.create(inferred)
    await db_session.commit()

    prefs = await repo.get_explicit_preferences("user-1")
    assert [m.content for m in prefs] == ["explicit pref"]


async def test_entity_get_or_create_is_idempotent_by_canonical_name(db_session) -> None:
    repo = EntityRepository(db_session)
    first = await repo.get_or_create("user-1", EntityType.PERSON.value, "Maya", "maya")
    second = await repo.get_or_create("user-1", EntityType.PERSON.value, "Maya", "maya")
    await db_session.commit()

    assert first.entity_id == second.entity_id


async def test_agent_manifest_roundtrip_preserves_eligibility(db_session) -> None:
    repo = AgentManifestRepository(db_session)
    manifest = AgentManifest(
        agent_id="internal-context-intelligence",
        name="Context Intelligence",
        ownership=AgentOwnership.INTERNAL,
        version="1.0.0",
        description="test",
        capabilities=["context.retrieve"],
        side_effect_level=SideEffectLevel.READ_ONLY,
        trust_status=AgentTrustStatus.APPROVED,
        enabled=True,
        health_status=AgentHealthStatus.HEALTHY,
        implementation_status=AgentImplementationStatus.FULLY_IMPLEMENTED,
    )
    await repo.upsert(manifest)
    await db_session.commit()

    stored = await repo.list_all()
    assert len(stored) == 1
    assert stored[0].is_eligible is True


async def test_user_profile_upsert_and_get(db_session) -> None:
    repo = UserProfileRepository(db_session)
    profile = UserProfile(
        user_id="user-dinethra",
        display_name="Dinethra",
        home_location=Location(label="Colombo", latitude=6.9271, longitude=79.8612),
        timezone="Asia/Colombo",
        food_preferences=FoodPreferences(cuisines=["italian"]),
        travel_preferences=TravelPreferences(interests=["hiking"]),
        calendar=CalendarConfig(),
        approval_policy=ApprovalPolicyConfig(),
    )
    await repo.upsert(profile)
    await db_session.commit()

    fetched = await repo.get("user-dinethra")
    assert fetched is not None
    assert fetched.display_name == "Dinethra"


async def test_seed_module_builds_six_agents_and_thirty_plus_memories() -> None:
    from demo.seed import SEED_MEMORIES, build_agent_catalogue

    assert len(SEED_MEMORIES) >= 30
    assert len(build_agent_catalogue()) == 6
