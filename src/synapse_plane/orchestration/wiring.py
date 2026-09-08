"""Composition root: builds the planner and agent registry for one request.

DEMO_MODE (the .env default: true) is the hard safety gate — it decides
between the deterministic fake/mock stack (FakePlanner, tool-backed demo
agents, no network) and the real Gemini/Tavily/Google stack. This is
deliberate and explicit: with real API keys now in .env, key *presence*
must never be what decides whether a live call happens, or every test run
would silently start spending quota the moment someone adds real keys.
Only DEMO_MODE=false does that, and nothing in this codebase sets it.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from synapse_plane.agents.base import BaseAgent
from synapse_plane.agents.internal.context_intelligence import ContextIntelligenceAgent
from synapse_plane.agents.internal.planning_decision import PlannerProtocol, PlanningDecisionAgent
from synapse_plane.config import Settings
from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.profile import UserProfile
from synapse_plane.memory.embedding_service import EmbeddingServiceProtocol, FakeEmbeddingService
from synapse_plane.observability.event_emitter import EventEmitter
from synapse_plane.orchestration.binding_resolver import BindingResolver
from synapse_plane.orchestration.executor import AgentExecutor
from synapse_plane.orchestration.scheduler import DependencyScheduler
from synapse_plane.persistence.execution_repositories import (
    ApprovalRepository,
    ExecutionEventRepository,
    ExecutionRepository,
    TaskAttemptRepository,
    TaskRepository,
)
from synapse_plane.persistence.repositories import (
    EntityRepository,
    ExternalActionRecordRepository,
    MemoryRepository,
)
from synapse_plane.planning.fake_planner import FakePlanner
from synapse_plane.policies.approval_policy import ApprovalPolicy
from synapse_plane.policies.retry_policy import RetryPolicy
from synapse_plane.registry.capability_router import CapabilityRouter
from synapse_plane.retrieval.context_retriever import HybridContextRetriever

DEMO_USER_ID = "user-dinethra"


def get_planner(settings: Settings) -> PlannerProtocol:
    if settings.demo_mode or not settings.openai_api_key:
        return FakePlanner()

    from synapse_plane.llm.gemini_client import make_gemini_client
    from synapse_plane.planning.intent_planner import IntentPlanner

    return IntentPlanner(make_gemini_client(settings), settings)


def get_embedding_service(settings: Settings) -> EmbeddingServiceProtocol:
    # No real embedding provider is wired yet (see docs/DECISIONS.md) —
    # always fake for now, regardless of DEMO_MODE.
    return FakeEmbeddingService()


def build_agent_registry(
    db: AsyncSession, settings: Settings, inject_failure: bool = False
) -> dict[str, BaseAgent]:
    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db),
        entity_repo=EntityRepository(db),
        embedding_service=get_embedding_service(settings),
        settings=settings,
    )
    registry: dict[str, BaseAgent] = {
        "internal-context-intelligence": ContextIntelligenceAgent(retriever),
        "internal-planning-decision": PlanningDecisionAgent(planner=get_planner(settings)),
    }

    if settings.demo_mode:
        from demo.agents import DemoCalendarAgent, DemoVenueDiscoveryAgent

        registry["external-browser-use"] = DemoVenueDiscoveryAgent(inject_failure=inject_failure)
        registry["external-openclaw-personal"] = DemoCalendarAgent(
            ExternalActionRecordRepository(db)
        )
    else:
        from synapse_plane.agents.external.browser_use_adapter import BrowserUseAdapter
        from synapse_plane.agents.external.openclaw_adapter import OpenClawAdapter
        from synapse_plane.llm.gemini_client import make_gemini_client
        from synapse_plane.tools.search_client import TavilySearchClient

        llm_client = make_gemini_client(settings) if settings.openai_api_key else None
        search_client = (
            TavilySearchClient(settings.tavily_api_key) if settings.tavily_api_key else None
        )
        registry["external-browser-use"] = BrowserUseAdapter(
            search_client=search_client, llm_client=llm_client, llm_model=settings.openai_model
        )

        if settings.calendar_provider == "google":
            from synapse_plane.tools.google_calendar_tool import (
                GoogleCalendarAuthRequiredError,
                GoogleCalendarTool,
                build_google_calendar_service,
            )

            try:
                service = build_google_calendar_service(settings.google_calendar_token_path)
                google_tool = GoogleCalendarTool(service, ExternalActionRecordRepository(db))
                registry["external-openclaw-personal"] = OpenClawAdapter(
                    read_tool=google_tool, write_tool=google_tool
                )
            except GoogleCalendarAuthRequiredError:
                registry["external-openclaw-personal"] = OpenClawAdapter()  # unavailable, honest
        else:
            registry["external-openclaw-personal"] = OpenClawAdapter()

    return registry


def build_scheduler(
    db: AsyncSession,
    settings: Settings,
    catalogue: list[AgentManifest],
    profile: UserProfile,
    inject_failure: bool = False,
) -> DependencyScheduler:
    db_lock = asyncio.Lock()
    agent_registry = build_agent_registry(db, settings, inject_failure=inject_failure)

    emitter = EventEmitter(ExecutionEventRepository(db))
    executor = AgentExecutor(
        router=CapabilityRouter(),
        agent_registry=agent_registry,
        binding_resolver=BindingResolver(),
        retry_policy=RetryPolicy(),
        approval_policy=ApprovalPolicy(),
        task_repo=TaskRepository(db),
        attempt_repo=TaskAttemptRepository(db),
        approval_repo=ApprovalRepository(db),
        emitter=emitter,
        db_lock=db_lock,
    )
    return DependencyScheduler(
        execution_repo=ExecutionRepository(db),
        task_repo=TaskRepository(db),
        executor=executor,
        emitter=emitter,
        catalogue=catalogue,
        profile=profile,
        base_context={
            "user_id": DEMO_USER_ID,
            "preferred_cuisines": profile.food_preferences.cuisines,
        },
        db_lock=db_lock,
    )
