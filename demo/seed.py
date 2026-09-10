"""Seed the demo user, memories, entities/relationships, and agent catalogue.
Run with: python -m demo.seed
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete

from synapse_plane.config import get_settings
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
from synapse_plane.orchestration.wiring import get_embedding_service
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
        display_name="Dinethra Rajapaksha",
        home_location=Location(label="Moratuwa, Sri Lanka", latitude=6.7730, longitude=79.8816),
        timezone="Asia/Colombo",
        language="en",
        currency="LKR",
        food_preferences=FoodPreferences(
            cuisines=["fast_food", "pizza", "sri_lankan", "italian"],
            dietary_restrictions=["no_shellfish"],
            price_level="moderate",
            max_distance_km=10.0,
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


# A detailed personal history, so recommendations can be checked against
# something specific ("did it pick pizza in Moratuwa for Rebecca, and a quiet
# Italian place for Maya?") rather than against a vague preference list.
# Mixed with deliberately irrelevant entries so retrieval has to discriminate.
SEED_MEMORIES: list[dict[str, object]] = [
    # ── Core identity and standing food preferences ──────────────────────
    {
        "type": MemoryType.PREFERENCE,
        "content": "My name is Dinethra Rajapaksha. I live in Moratuwa and work in Colombo 03.",
        "confidence": 0.99,
        "explicit": True,
        "days_ago": 400,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I love fast food — burgers, fried chicken and especially pizza.",
        "confidence": 0.95,
        "explicit": True,
        "days_ago": 120,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Pizza is my favourite food. Thin crust with extra cheese is my usual order.",
        "confidence": 0.93,
        "explicit": True,
        "days_ago": 95,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I drink a lot of fresh fruit juice — woodapple and mango are my favourites.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 110,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I drink coffee daily, usually a flat white in the morning and after dinner.",
        "confidence": 0.92,
        "explicit": True,
        "days_ago": 88,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I am allergic to shellfish — no prawns, crab or cuttlefish in my food.",
        "confidence": 0.99,
        "explicit": True,
        "days_ago": 500,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I dislike very spicy food beyond medium heat level.",
        "confidence": 0.88,
        "explicit": True,
        "days_ago": 150,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I also enjoy Sri Lankan traditional food — rice and curry, kottu, hoppers.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 75,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Usually finish work around 6:30 PM. Prefer dinner no earlier than 7PM.",
        "confidence": 0.92,
        "explicit": True,
        "days_ago": 90,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "My dinner budget is moderate — around LKR 4000-6000 for two people.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 60,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Trying to cut down on expensive restaurant meals this month. Budget: moderate.",
        "confidence": 0.8,
        "explicit": True,
        "days_ago": 5,
    },
    # ── Maya: quiet, Italian, Sri Lankan traditional, vegetarian-leaning ──
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Maya is my colleague and I have been on dates with her before.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 60,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "I went on a date with Maya to an Italian restaurant and it went really well.",
        "confidence": 0.92,
        "explicit": True,
        "days_ago": 45,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Maya loves Italian food — pasta and wood-fired pizza especially.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 60,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Maya and I both love Sri Lankan traditional food, especially rice and curry.",
        "confidence": 0.88,
        "explicit": True,
        "days_ago": 40,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Maya prefers quiet restaurants where we can actually talk.",
        "confidence": 0.94,
        "explicit": True,
        "days_ago": 42,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Maya mentioned she is trying to eat more vegetarian meals during the week.",
        "confidence": 0.78,
        "explicit": False,
        "days_ago": 10,
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
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 20,
    },
    # ── Rebecca: fast food, pizza, Moratuwa chains ───────────────────────
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Rebecca is my close friend from university and we eat out often.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 200,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Rebecca loves fast food — she always wants pizza or fried chicken.",
        "confidence": 0.92,
        "explicit": True,
        "days_ago": 100,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Rebecca and I ate at Pizza Hut Moratuwa — we both loved the pan pizza.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 70,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Went to Burger King Moratuwa with Rebecca after a movie. Quick and cheap.",
        "confidence": 0.87,
        "explicit": True,
        "days_ago": 55,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Ordered from Domino's Moratuwa with Rebecca — delivery was fast, pizza good.",
        "confidence": 0.86,
        "explicit": True,
        "days_ago": 30,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "When I go out with Rebecca we prefer casual, lively fast food places.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 50,
    },
    # ── Sithma: breakfast/brunch, coffee, quiet cafes ────────────────────
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Sithma is my cousin who lives nearby in Moratuwa. We meet for breakfast often.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 80,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Sithma loves breakfast and brunch places, and always orders good coffee.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 60,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Had breakfast with Sithma at a quiet cafe in Mount Lavinia last month.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 35,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Sithma dislikes fast food and prefers healthier, home-style breakfast options.",
        "confidence": 0.87,
        "explicit": True,
        "days_ago": 40,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Sithma and I are planning to visit Kandy together next month for the weekend.",
        "confidence": 0.8,
        "explicit": True,
        "days_ago": 8,
    },
    # ── Amal: strict vegetarian, health-conscious ────────────────────────
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Amal is my gym friend. He is a strict vegetarian and quite health-conscious.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 90,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Amal never eats meat, fish or eggs — needs a proper vegetarian menu.",
        "confidence": 0.93,
        "explicit": True,
        "days_ago": 90,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Had lunch with Amal at a vegetarian place near the gym — he loved the salads.",
        "confidence": 0.85,
        "explicit": True,
        "days_ago": 25,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Amal prefers healthy, low-oil food and avoids fast food entirely.",
        "confidence": 0.88,
        "explicit": True,
        "days_ago": 60,
    },
    # ── Dining habits and dislikes ───────────────────────────────────────
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer quiet restaurants over lively, noisy ones for proper conversations.",
        "confidence": 0.95,
        "explicit": True,
        "days_ago": 40,
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
        "content": "Last visit to Bella Roma — it was really crowded and noisy, I didn't enjoy it.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 28,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I don't like buffets — I would rather order a proper plated meal.",
        "confidence": 0.8,
        "explicit": True,
        "days_ago": 65,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer places with parking, since I drive from Moratuwa most evenings.",
        "confidence": 0.82,
        "explicit": True,
        "days_ago": 85,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Tried Nuga Gama for Sri Lankan food last year — loved the traditional setting.",
        "confidence": 0.84,
        "explicit": True,
        "days_ago": 180,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "Friday and Saturday evenings are when I usually go out for dinner.",
        "confidence": 0.86,
        "explicit": True,
        "days_ago": 70,
    },
    # ── Travel (second use case) ─────────────────────────────────────────
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
        "confidence": 0.7,
        "explicit": True,
        "days_ago": 400,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I want to actually see the Temple of the Tooth in Kandy this time.",
        "confidence": 0.8,
        "explicit": True,
        "days_ago": 8,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer travelling by train over the bus when going to Kandy — better views.",
        "confidence": 0.75,
        "explicit": True,
        "days_ago": 90,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "In Galle I'd want to see the fort, the lighthouse, and try fresh seafood — "
        "wait, no, I'm allergic to shellfish, so grilled fish instead.",
        "confidence": 0.7,
        "explicit": True,
        "days_ago": 8,
    },
    {
        "type": MemoryType.GOAL,
        "content": "Keeping travel budget under LKR 30,000 for the next short trip.",
        "confidence": 0.75,
        "explicit": True,
        "days_ago": 3,
    },
    # ── Irrelevant — retrieval must exclude / down-rank these ────────────
    {
        "type": MemoryType.GOAL,
        "content": "I want to finish reading 12 books this year. Currently on book 7.",
        "confidence": 0.7,
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
        "confidence": 0.6,
        "explicit": True,
        "days_ago": 200,
    },
    {
        "type": MemoryType.RELATIONSHIP,
        "content": "Kasun is my university friend. He works in Singapore now.",
        "confidence": 0.8,
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
        "confidence": 0.6,
        "explicit": True,
        "days_ago": 30,
    },
    {
        "type": MemoryType.PREFERENCE,
        "content": "I prefer dark mode in every app I use.",
        "confidence": 0.9,
        "explicit": True,
        "days_ago": 500,
    },
    {
        "type": MemoryType.EPISODIC,
        "content": "Watched a documentary about deep-sea exploration last weekend.",
        "confidence": 0.5,
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
        "type": MemoryType.GOAL,
        "content": "Saving up for a new camera lens by year end.",
        "confidence": 0.58,
        "explicit": True,
        "days_ago": 35,
    },
]

SEED_ENTITIES: list[dict[str, str]] = [
    {"type": EntityType.USER.value, "name": "Dinethra Rajapaksha", "canonical_name": "user"},
    # People
    {"type": EntityType.PERSON.value, "name": "Maya", "canonical_name": "maya"},
    {"type": EntityType.PERSON.value, "name": "Rebecca", "canonical_name": "rebecca"},
    {"type": EntityType.PERSON.value, "name": "Sithma", "canonical_name": "sithma"},
    {"type": EntityType.PERSON.value, "name": "Amal", "canonical_name": "amal"},
    {"type": EntityType.PERSON.value, "name": "Kasun", "canonical_name": "kasun"},
    {"type": EntityType.PERSON.value, "name": "Nadeesha", "canonical_name": "nadeesha"},
    # Places eaten at before — these are what a recommendation can be checked against
    {"type": EntityType.RESTAURANT.value, "name": "Bella Roma", "canonical_name": "bella_roma"},
    {"type": EntityType.RESTAURANT.value, "name": "La Foresta", "canonical_name": "la_foresta"},
    {
        "type": EntityType.RESTAURANT.value,
        "name": "Pizza Hut Moratuwa",
        "canonical_name": "pizza_hut_moratuwa",
    },
    {
        "type": EntityType.RESTAURANT.value,
        "name": "Burger King Moratuwa",
        "canonical_name": "burger_king_moratuwa",
    },
    {
        "type": EntityType.RESTAURANT.value,
        "name": "Domino's Moratuwa",
        "canonical_name": "dominos_moratuwa",
    },
    {"type": EntityType.RESTAURANT.value, "name": "Nuga Gama", "canonical_name": "nuga_gama"},
    # Preferences as first-class nodes, so the graph can connect people to them
    {
        "type": EntityType.PREFERENCE.value,
        "name": "Quiet Restaurants",
        "canonical_name": "quiet_restaurants",
    },
    {"type": EntityType.PREFERENCE.value, "name": "Pizza", "canonical_name": "pizza"},
    {"type": EntityType.PREFERENCE.value, "name": "Fast Food", "canonical_name": "fast_food"},
    {
        "type": EntityType.PREFERENCE.value,
        "name": "Italian Food",
        "canonical_name": "italian_food",
    },
    {
        "type": EntityType.PREFERENCE.value,
        "name": "Sri Lankan Traditional Food",
        "canonical_name": "sri_lankan_food",
    },
    {"type": EntityType.PREFERENCE.value, "name": "Fruit Juice", "canonical_name": "fruit_juice"},
    {"type": EntityType.PREFERENCE.value, "name": "Coffee", "canonical_name": "coffee"},
    {"type": EntityType.PREFERENCE.value, "name": "Breakfast", "canonical_name": "breakfast_food"},
    {
        "type": EntityType.PREFERENCE.value,
        "name": "Vegetarian Food",
        "canonical_name": "vegetarian_food",
    },
    {
        "type": EntityType.PREFERENCE.value,
        "name": "Shellfish Allergy",
        "canonical_name": "shellfish_allergy",
    },
    # Places
    {"type": EntityType.PLACE.value, "name": "Moratuwa", "canonical_name": "moratuwa"},
    {"type": EntityType.PLACE.value, "name": "Kandy", "canonical_name": "kandy"},
    {"type": EntityType.PLACE.value, "name": "Galle", "canonical_name": "galle"},
]

# (source_canonical_name, relationship_type, target_canonical_name)
SEED_RELATIONSHIPS: list[tuple[str, str, str]] = [
    # Who the user knows
    ("user", "KNOWS", "maya"),
    ("user", "KNOWS", "rebecca"),
    ("user", "KNOWS", "sithma"),
    ("user", "KNOWS", "amal"),
    ("user", "KNOWS", "kasun"),
    ("user", "KNOWS", "nadeesha"),
    # What the user likes / avoids
    ("user", "LIVES_IN", "moratuwa"),
    ("user", "PREFERS", "pizza"),
    ("user", "PREFERS", "fast_food"),
    ("user", "PREFERS", "sri_lankan_food"),
    ("user", "PREFERS", "fruit_juice"),
    ("user", "PREFERS", "coffee"),
    ("user", "PREFERS", "quiet_restaurants"),
    ("user", "AVOIDS", "shellfish_allergy"),
    ("user", "AVOIDS", "bella_roma"),
    # Maya — the quiet / Italian / Sri Lankan side
    ("maya", "PREFERS", "quiet_restaurants"),
    ("maya", "PREFERS", "italian_food"),
    ("maya", "PREFERS", "sri_lankan_food"),
    ("user", "VISITED", "la_foresta"),
    # Rebecca — the fast food / Moratuwa side
    ("rebecca", "PREFERS", "fast_food"),
    ("rebecca", "PREFERS", "pizza"),
    ("user", "VISITED", "pizza_hut_moratuwa"),
    ("user", "VISITED", "burger_king_moratuwa"),
    ("user", "VISITED", "dominos_moratuwa"),
    ("user", "VISITED", "nuga_gama"),
    ("pizza_hut_moratuwa", "LOCATED_IN", "moratuwa"),
    ("burger_king_moratuwa", "LOCATED_IN", "moratuwa"),
    ("dominos_moratuwa", "LOCATED_IN", "moratuwa"),
    # Sithma — breakfast, coffee, quiet cafes
    ("sithma", "PREFERS", "breakfast_food"),
    ("sithma", "PREFERS", "coffee"),
    ("sithma", "PREFERS", "quiet_restaurants"),
    ("sithma", "LIVES_IN", "moratuwa"),
    # Amal — strict vegetarian, health-conscious
    ("amal", "PREFERS", "vegetarian_food"),
    ("nadeesha", "LIVES_IN", "kandy"),
]


def build_agent_catalogue() -> list[AgentManifest]:
    """The 6 real agents in the catalogue."""
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
            source_repository="tavily.com (search-based substitute for browser-use/browser-use; "
            "no Playwright/Chromium install in this environment — see docs/DECISIONS.md)",
            version="0.1.0",
            description="Discovers and verifies restaurant candidates via Tavily web search + "
            "Gemini extraction. Receives only the search goal and location, never full memory.",
            capabilities=[
                "web.discover_places",
                "web.navigate",
                "web.extract",
                "web.verify_information",
            ],
            protocol="http",
            side_effect_level=SideEffectLevel.READ_ONLY,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.DEGRADED,
            implementation_status=AgentImplementationStatus.CONFIGURED,
            reliability_score=0.75,
            estimated_latency_ms=15000,
            timeout_seconds=60,
            tags=["external", "web", "venue-discovery"],
        ),
        AgentManifest(
            agent_id="external-open-deep-research",
            name="Open Deep Research Agent",
            ownership=AgentOwnership.EXTERNAL,
            source_repository="tavily.com + Gemini synthesis (no langchain-ai/open_deep_research "
            "LangGraph server running — implemented directly, see docs/DECISIONS.md)",
            version="0.1.0",
            description="Multi-step research agent — investigates destinations and compares "
            "evidence from multiple Tavily-searched sources for the travel use case.",
            capabilities=[
                "research.deep",
                "travel.destination_research",
                "alternatives.evidence_comparison",
            ],
            protocol="http",
            side_effect_level=SideEffectLevel.READ_ONLY,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.HEALTHY,
            implementation_status=AgentImplementationStatus.CONFIGURED,
            reliability_score=0.70,
            estimated_latency_ms=45000,
            timeout_seconds=60,
            tags=["external", "research", "travel"],
        ),
        AgentManifest(
            agent_id="external-openclaw-personal",
            name="OpenClaw Personal Action Agent",
            ownership=AgentOwnership.EXTERNAL,
            source_repository="Google Calendar API directly in real mode, mock calendar tools "
            "in DEMO_MODE (no openclaw/openclaw MCP gateway running — see docs/DECISIONS.md)",
            version="0.1.0",
            description="Personal assistant agent — checks calendar availability and creates "
            "approved events. Consequential writes require a stored ApprovalProposal. Falls back "
            "to reporting unavailable if real mode is active and Google OAuth isn't set up yet.",
            capabilities=[
                "personal.calendar_availability",
                "personal.calendar_create",
                "personal.task_create",
            ],
            protocol="http",
            side_effect_level=SideEffectLevel.MIXED,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.HEALTHY,
            implementation_status=AgentImplementationStatus.CONFIGURED,
            reliability_score=0.70,
            estimated_latency_ms=2000,
            tags=["external", "calendar", "google"],
        ),
        AgentManifest(
            agent_id="external-weather",
            name="Weather Agent",
            ownership=AgentOwnership.EXTERNAL,
            source_repository="Open-Meteo API (free, no API key) in real mode; deterministic "
            "hash-derived forecast in DEMO_MODE",
            version="0.1.0",
            description="Checks the forecast for a dinner date or a travel destination — shared "
            "by both use cases, since rain matters for outdoor seating and for a hiking trip "
            "alike. Never blocks a plan; a missing forecast degrades to 'no data', not a failure.",
            capabilities=["weather.check"],
            protocol="http",
            side_effect_level=SideEffectLevel.READ_ONLY,
            trust_status=AgentTrustStatus.APPROVED,
            enabled=True,
            health_status=AgentHealthStatus.HEALTHY,
            implementation_status=AgentImplementationStatus.CONFIGURED,
            reliability_score=0.85,
            estimated_latency_ms=3000,
            tags=["external", "weather", "dining", "travel"],
        ),
    ]


async def seed() -> None:
    """Runs on every container start (see docker-compose.yml) — must be
    idempotent. Entities/profile/agents already use get_or_create/upsert;
    memories and relationships didn't, and re-ran additively on every
    restart (confirmed: 608 memory rows / 133 relationships in a database
    restarted ~19 times during one session, for what should be 32 / 7).
    Clearing this demo user's memories/relationships first makes reseeding
    safe to run any number of times.
    """
    from synapse_plane.persistence.models import (
        MemoryEmbeddingModel,
        MemoryEntityModel,
        MemoryModel,
        RelationshipModel,
    )

    session_factory = get_session_factory()
    # Real embeddings in real mode, same as everything else — a memory
    # embedded with the fake service while running for real would never be
    # findable by a real query embedding (they're different, incompatible
    # vector spaces even at the same dimension).
    embedding_service = get_embedding_service(get_settings())

    async with session_factory() as session:
        profile_repo = UserProfileRepository(session)
        memory_repo = MemoryRepository(session)
        entity_repo = EntityRepository(session)
        agent_repo = AgentManifestRepository(session)

        await profile_repo.upsert(build_profile())

        existing_memory_ids = (
            (
                await session.execute(
                    MemoryModel.__table__.select()
                    .with_only_columns(MemoryModel.id)
                    .where(MemoryModel.user_id == USER_ID)
                )
            )
            .scalars()
            .all()
        )
        if existing_memory_ids:
            await session.execute(
                delete(MemoryEmbeddingModel).where(
                    MemoryEmbeddingModel.memory_id.in_(existing_memory_ids)
                )
            )
            # No FK cascade on memory_entities -> memories: deleting a memory
            # that still has entity links would fail with a constraint
            # violation, which is exactly what this fix now needs to clean
            # up (memories are now linked to entities — see the seeding loop
            # below).
            await session.execute(
                delete(MemoryEntityModel).where(
                    MemoryEntityModel.memory_id.in_(existing_memory_ids)
                )
            )
            await session.execute(delete(MemoryModel).where(MemoryModel.user_id == USER_ID))
        await session.execute(delete(RelationshipModel).where(RelationshipModel.user_id == USER_ID))

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

            # Link this memory to every entity it actually names — the same
            # substring match get_related_memories relies on at query time
            # (EntityRepository.find_mentioned). Without this, the entity/
            # relationship graph traversal is real code with nothing to
            # return: it BFS-expands correctly but the final join against
            # memory_entities always came back empty (confirmed: 0 rows,
            # since nothing ever called link_to_memory before this).
            lowered_content = content.lower()
            for entity_spec in SEED_ENTITIES:
                canonical = entity_spec["canonical_name"]
                name = entity_spec["name"].lower()
                if canonical.replace("_", " ") in lowered_content or name in lowered_content:
                    await entity_repo.link_to_memory(
                        entity_by_canonical[canonical], memory.memory_id, role="mentions"
                    )

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
