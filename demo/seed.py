"""Seed the demo user, memories, entities/relationships, and agent catalogue.
Run with: python -m demo.seed
"""

import asyncio
from datetime import UTC, datetime, timedelta
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
from synapse_plane.persistence.database import get_session_factory
from synapse_plane.persistence.repositories import (
    AgentManifestRepository,
    EntityRepository,
    MemoryRepository,
    UserProfileRepository,
)

USER_ID = "user-dinethra"


def _now() -> datetime:
    return datetime.now(UTC)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def build_profile() -> UserProfile:
    return UserProfile(
        user_id=USER_ID,
        display_name="Dinethra",
        home_location=Location(label="Colombo 03, Sri Lanka", latitude=6.9147, longitude=79.8500),
        timezone="Asia/Colombo",
        language="en",
        currency="LKR",
        food_preferences=FoodPreferences(
            cuisines=["italian", "sri_lankan", "japanese"],
            dietary_restrictions=[],
            price_level="moderate",
            max_distance_km=8.0,
            preferred_dinner_time="19:30",
        ),
        travel_preferences=TravelPreferences(
            interests=["hiking", "history", "food"],
            walking_tolerance="moderate",
            pace="normal",
        ),
        calendar=CalendarConfig(provider="mock", calendar_id="primary"),
        approval_policy=ApprovalPolicyConfig(
            require_for_external_writes=True, require_for_financial_actions=True
        ),
    )


# mixed relevant / irrelevant memories, so retrieval has to discriminate
SEED_MEMORIES: list[dict[str, object]] = [
    # Relevant to the dinner-with-Maya scenario
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer quiet restaurants over lively, noisy ones",
        "confidence": 0.95,
        "explicit": True,
        "days_ago": 40,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Last visit to Bella Roma — it was really crowded and noisy, I didn't enjoy it",
        "confidence": 0.90,
        "explicit": True,
        "days_ago": 28,
    },
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Maya is my colleague. She loves Italian food and is vegetarian-friendly.",
        "confidence": 0.88,
        "explicit": True,
        "days_ago": 60,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Trying to cut down on expensive restaurant meals this month. Budget: moderate.",
        "confidence": 0.80,
        "explicit": True,
        "days_ago": 5,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Usually finish work around 6:30 PM. Prefer dinner no earlier than 7PM.",
        "confidence": 0.92,
        "explicit": True,
        "days_ago": 90,
    },
    {
        "type": MemoryType.DECISION,
        "content": "Chose La Foresta for dinner with Maya in August — she loved the quiet.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 20,
    },
    {
        "type": MemoryType.OUTCOME,
        "content": "Calendar event for La Foresta dinner created; Maya confirmed attendance.",
        "confidence": 0.90,
        "explicit": True,
        "days_ago": 20,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I avoid restaurants with live music — too distracting for conversation.",
        "confidence": 0.83,
        "explicit": True,
        "days_ago": 15,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Maya mentioned she is trying to eat more vegetarian meals during the week.",
        "confidence": 0.78,
        "explicit": False,
        "days_ago": 10,
    },
    # Relevant to the travel scenario (Kandy vs Galle)
    {
        "type": MemoryType.GOAL,
        "content": "Planning a short two-day trip next month, thinking Kandy or Galle.",
        "confidence": 0.82,
        "explicit": True,
        "days_ago": 3,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I enjoy historical sites and moderate hiking when travelling.",
        "confidence": 0.87,
        "explicit": True,
        "days_ago": 100,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Trip to Galle last year with family. Loved walking the old fort ramparts.",
        "confidence": 0.78,
        "explicit": True,
        "days_ago": 200,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Visited Kandy for a conference; didn't get to see the Temple of the Tooth.",
        "confidence": 0.70,
        "explicit": True,
        "days_ago": 400,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Keeping travel budget under LKR 30,000 for the next short trip.",
        "confidence": 0.75,
        "explicit": True,
        "days_ago": 3,
    },
    # Irrelevant — retriever must exclude / down-rank these
    {
        "type": MemoryType.GOAL,
        "content": "I want to finish reading 12 books this year. Currently on book 7.",
        "confidence": 0.70,
        "explicit": True,
        "days_ago": 50,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Attended a React conference last Thursday. Very useful talks on performance.",
        "confidence": 0.75,
        "explicit": True,
        "days_ago": 4,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer morning gym sessions over evening ones.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 120,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Learning Spanish — targeting B1 level by March.",
        "confidence": 0.72,
        "explicit": True,
        "days_ago": 60,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Had a productive deep-work session this morning. Completed the API refactor.",
        "confidence": 0.65,
        "explicit": True,
        "days_ago": 1,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I like using mechanical keyboards. Currently using a Keychron K2.",
        "confidence": 0.60,
        "explicit": True,
        "days_ago": 200,
    },
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Kasun is my university friend. He works in Singapore now.",
        "confidence": 0.80,
        "explicit": True,
        "days_ago": 300,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Want to contribute to an open-source project before year end.",
        "confidence": 0.68,
        "explicit": True,
        "days_ago": 45,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer aisle seats on flights.",
        "confidence": 0.66,
        "explicit": True,
        "days_ago": 250,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Fixed a flaky CI pipeline at work — turned out to be a timezone bug.",
        "confidence": 0.55,
        "explicit": True,
        "days_ago": 12,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Trying to drink more water during the day, aiming for 2 litres.",
        "confidence": 0.60,
        "explicit": True,
        "days_ago": 30,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer dark mode in every app I use.",
        "confidence": 0.90,
        "explicit": True,
        "days_ago": 500,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Watched a documentary about deep-sea exploration last weekend.",
        "confidence": 0.50,
        "explicit": True,
        "days_ago": 7,
    },
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "My sister Nadeesha is a doctor in Kandy.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 400,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Considering switching from a MacBook to a Linux laptop for personal projects.",
        "confidence": 0.55,
        "explicit": True,
        "days_ago": 22,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Went for a 10km run on Sunday morning along Galle Face Green.",
        "confidence": 0.62,
        "explicit": True,
        "days_ago": 6,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I dislike very spicy food beyond medium heat level.",
        "confidence": 0.88,
        "explicit": True,
        "days_ago": 150,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Saving up for a new camera lens by year end.",
        "confidence": 0.58,
        "explicit": True,
        "days_ago": 35,
    },
]

SEED_ENTITIES: list[dict[str, str]] = [
    {"type": EntityType.USER.value, "name": "Dinethra", "canonical_name": "user"},
    {"type": EntityType.PERSON.value, "name": "Maya", "canonical_name": "maya"},
    {"type": EntityType.PERSON.value, "name": "Kasun", "canonical_name": "kasun"},
    {"type": EntityType.PERSON.value, "name": "Nadeesha", "canonical_name": "nadeesha"},
    {"type": EntityType.RESTAURANT.value, "name": "Bella Roma", "canonical_name": "bella_roma"},
    {"type": EntityType.RESTAURANT.value, "name": "La Foresta", "canonical_name": "la_foresta"},
    {
        "type": EntityType.PREFERENCE.value,
        "name": "Quiet Restaurants",
        "canonical_name": "quiet_restaurants",
    },
    {"type": EntityType.PLACE.value, "name": "Kandy", "canonical_name": "kandy"},
    {"type": EntityType.PLACE.value, "name": "Galle", "canonical_name": "galle"},
]

# (source_canonical_name, relationship_type, target_canonical_name)
SEED_RELATIONSHIPS: list[tuple[str, str, str]] = [
    ("user", "KNOWS", "maya"),
    ("maya", "PREFERS", "quiet_restaurants"),
    ("user", "PREFERS", "quiet_restaurants"),
    ("user", "AVOIDS", "bella_roma"),
    ("user", "KNOWS", "kasun"),
    ("user", "KNOWS", "nadeesha"),
    ("nadeesha", "LIVES_IN", "kandy"),
]


def build_agent_catalogue() -> list[AgentManifest]:
    """The 5 real agents in the catalogue."""
    return [
        AgentManifest(
            agent_id="internal-context-intelligence",
            name="Context Intelligence Agent",
            ownership=AgentOwnership.INTERNAL,
            version="1.0.0",
            description="Hybrid RAG retrieval — interprets intent, retrieves relevant memories, "
            "traverses the entity graph, builds a grounded context package.",
            capabilities=["context.retrieve", "memory.resolve_entities", "context.build_package"],
            protocol="internal",
            side_effect_level=SideEffectLevel.READ_ONLY,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.HEALTHY,
            implementation_status=AgentImplementationStatus.FULLY_IMPLEMENTED,
            reliability_score=0.97,
            estimated_latency_ms=400,
            tags=["memory", "rag", "internal"],
        ),
        AgentManifest(
            agent_id="internal-planning-decision",
            name="Planning & Decision Agent",
            ownership=AgentOwnership.INTERNAL,
            version="1.0.0",
            description="Proposes the task DAG, compares alternatives, generates grounded "
            "recommendations, and re-plans on failure. Proposes only — never executes.",
            capabilities=[
                "workflow.plan",
                "workflow.replan",
                "alternatives.compare",
                "recommendation.synthesize",
            ],
            protocol="internal",
            side_effect_level=SideEffectLevel.NONE,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.HEALTHY,
            implementation_status=AgentImplementationStatus.FULLY_IMPLEMENTED,
            reliability_score=0.95,
            estimated_latency_ms=800,
            tags=["planning", "llm", "internal"],
        ),
        AgentManifest(
            agent_id="external-browser-use",
            name="Browser Use Web Agent",
            ownership=AgentOwnership.EXTERNAL,
            source_repository="browser-use/browser-use",
            version="0.1.0",
            description="Live browser agent — discovers restaurants and verifies venue details "
            "on real websites. Receives only the search goal and location, never full memory.",
            capabilities=[
                "web.discover_places",
                "web.navigate",
                "web.extract",
                "web.verify_information",
            ],
            protocol="subprocess",
            side_effect_level=SideEffectLevel.READ_ONLY,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.DEGRADED,
            implementation_status=AgentImplementationStatus.LIVE_EXTERNAL,
            reliability_score=0.75,
            estimated_latency_ms=15000,
            timeout_seconds=60,
            tags=["external", "web", "venue-discovery"],
        ),
        AgentManifest(
            agent_id="external-open-deep-research",
            name="Open Deep Research Agent",
            ownership=AgentOwnership.EXTERNAL,
            source_repository="langchain-ai/open_deep_research",
            version="0.1.0",
            description="Multi-step research agent — investigates destinations and compares "
            "evidence from multiple sources for the travel use case.",
            capabilities=[
                "research.deep",
                "travel.destination_research",
                "alternatives.evidence_comparison",
            ],
            protocol="http",
            side_effect_level=SideEffectLevel.READ_ONLY,
            trust_status=AgentTrustStatus.PENDING_REVIEW,
            enabled=False,
            health_status=AgentHealthStatus.UNAVAILABLE,
            implementation_status=AgentImplementationStatus.REGISTERED_NOT_CONFIGURED,
            reliability_score=0.70,
            estimated_latency_ms=45000,
            timeout_seconds=60,
            tags=["external", "research", "travel"],
        ),
        AgentManifest(
            agent_id="external-openclaw-personal",
            name="OpenClaw Personal Action Agent",
            ownership=AgentOwnership.EXTERNAL,
            source_repository="openclaw/openclaw",
            version="0.1.0",
            description="Personal assistant runtime — checks calendar availability and creates "
            "approved events via MCP. Consequential writes require a stored ApprovalProposal.",
            capabilities=[
                "personal.calendar_availability",
                "personal.calendar_create",
                "personal.task_create",
            ],
            protocol="mcp",
            side_effect_level=SideEffectLevel.MIXED,
            trust_status=AgentTrustStatus.PENDING_REVIEW,
            enabled=False,
            health_status=AgentHealthStatus.UNAVAILABLE,
            implementation_status=AgentImplementationStatus.REGISTERED_NOT_CONFIGURED,
            reliability_score=0.70,
            estimated_latency_ms=2000,
            tags=["external", "mcp", "calendar"],
        ),
    ]


async def seed() -> None:
    session_factory = get_session_factory()
    embedding_service = FakeEmbeddingService()

    async with session_factory() as session:
        profile_repo = UserProfileRepository(session)
        memory_repo = MemoryRepository(session)
        entity_repo = EntityRepository(session)
        agent_repo = AgentManifestRepository(session)

        await profile_repo.upsert(build_profile())

        entity_by_canonical: dict[str, str] = {}
        for entity_spec in SEED_ENTITIES:
            entity = await entity_repo.get_or_create(
                user_id=USER_ID,
                entity_type=entity_spec["type"],
                name=entity_spec["name"],
                canonical_name=entity_spec["canonical_name"],
            )
            entity_by_canonical[entity_spec["canonical_name"]] = entity.entity_id

        for memory_spec in SEED_MEMORIES:
            content = str(memory_spec["content"])
            memory = Memory(
                memory_id=str(uuid4()),
                user_id=USER_ID,
                memory_type=memory_spec["type"],  # type: ignore[arg-type]
                content=content,
                confidence=float(memory_spec["confidence"]),  # type: ignore[arg-type]
                explicit_or_inferred=(
                    ExplicitOrInferred.EXPLICIT
                    if memory_spec["explicit"]
                    else ExplicitOrInferred.INFERRED
                ),
                valid_from=_days_ago(int(memory_spec["days_ago"])),  # type: ignore[arg-type]
                source="demo_seed",
                created_at=_now(),
                observed_at=_days_ago(int(memory_spec["days_ago"])),  # type: ignore[arg-type]
            )
            await memory_repo.create(memory)
            embedding = await embedding_service.embed(content)
            await memory_repo.store_embedding(memory.memory_id, embedding, embedding_service.model)

        for source_name, rel_type, target_name in SEED_RELATIONSHIPS:
            source_id = entity_by_canonical.get(source_name)
            target_id = entity_by_canonical.get(target_name)
            if source_id is None or target_id is None:
                continue
            from synapse_plane.persistence.models import RelationshipModel

            session.add(
                RelationshipModel(
                    id=str(uuid4()),
                    user_id=USER_ID,
                    source_entity_id=source_id,
                    relationship_type=rel_type,
                    target_entity_id=target_id,
                    weight=1.0,
                    valid_from=_now(),
                    valid_to=None,
                    source_memory_id=None,
                )
            )

        for manifest in build_agent_catalogue():
            await agent_repo.upsert(manifest)

        await session.commit()

    print(f"Seeded profile for {USER_ID}")
    print(f"Seeded {len(SEED_MEMORIES)} memories with embeddings")
    print(f"Seeded {len(SEED_ENTITIES)} entities and {len(SEED_RELATIONSHIPS)} relationships")
    print(f"Seeded {len(build_agent_catalogue())} agent manifests")


if __name__ == "__main__":
    asyncio.run(seed())
