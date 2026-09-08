"""Integration tests for the orchestration engine — real DB, FakePlanner.

The two external agents (browser-use, openclaw) aren't installed/configured
in this environment, so this test uses stand-in fakes with the SAME agent_id
as the real catalogue entries, backed by our real deterministic tools. This
is exactly the "fake agents" test category — it proves the engine (scheduler,
executor, retry/fallback, approval gate) works, not that browser-use itself
works.
"""

import asyncio

from demo.seed import build_agent_catalogue, build_profile

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.internal.context_intelligence import ContextIntelligenceAgent
from synapse_plane.agents.internal.planning_decision import PlanningDecisionAgent
from synapse_plane.config import Settings
from synapse_plane.domain.enums import (
    AgentHealthStatus,
    AgentImplementationStatus,
    AgentTrustStatus,
    ApprovalStatus,
    ExecutionStatus,
    TaskStatus,
)
from synapse_plane.domain.tools import CalendarEventRequest, RestaurantSearchRequest
from synapse_plane.memory.embedding_service import FakeEmbeddingService
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
    WorkflowVersionRepository,
)
from synapse_plane.persistence.repositories import (
    EntityRepository,
    ExternalActionRecordRepository,
    MemoryRepository,
)
from synapse_plane.planning.fake_planner import DINNER_WORKFLOW_PLAN, FakePlanner
from synapse_plane.policies.approval_policy import ApprovalPolicy
from synapse_plane.policies.retry_policy import RetryPolicy
from synapse_plane.registry.capability_router import CapabilityRouter
from synapse_plane.retrieval.context_retriever import HybridContextRetriever
from synapse_plane.tools.calendar_tool import CalendarReadTool, CalendarWriteTool
from synapse_plane.tools.places_tool import PlacesTool

USER_ID = "user-dinethra"


# Stand-in for external-browser-use — wraps PlacesTool
class FakeVenueDiscoveryAgent(BaseAgent):
    agent_id = "external-browser-use"

    def __init__(self):
        self.tool = PlacesTool()

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        candidates = await self.tool.search(RestaurantSearchRequest(location_label="Colombo"))
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={"candidates": [c.model_dump(mode="json") for c in candidates]},
            confidence=0.85,
        )

    def health_check(self) -> bool:
        return True


# Stand-in for external-openclaw-personal — wraps calendar tools
class FakeCalendarAgent(BaseAgent):
    agent_id = "external-openclaw-personal"

    def __init__(self, action_repo: ExternalActionRecordRepository, inject_failure: bool = False):
        self.read_tool = CalendarReadTool()
        self.write_tool = CalendarWriteTool(action_repo)
        self.inject_failure = inject_failure

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if agent_input.required_capability == "personal.calendar_create":
            recommendation = agent_input.context.get("recommendation", {})
            availability = agent_input.context.get("availability", {})
            selected = recommendation.get("selected", recommendation)
            request = CalendarEventRequest(
                title=f"Dinner at {selected.get('name', 'Restaurant')}",
                start_time=availability["start_time"],
                end_time=availability["end_time"],
                calendar_id="primary",
            )
            idempotency_key = f"{agent_input.execution_id}:{agent_input.task_id}:1"
            result = await self.write_tool.create_event(request, idempotency_key)
            return AgentOutput(
                task_id=agent_input.task_id,
                agent_id=self.agent_id,
                success=True,
                result=result.model_dump(mode="json"),
                confidence=0.9,
            )

        slots = await self.read_tool.get_availability(USER_ID, "2026-09-10")
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=slots[0].model_dump(mode="json"),
            confidence=0.9,
        )

    def health_check(self) -> bool:
        return True


async def _build_scheduler(db_session, catalogue, profile, agent_registry):
    execution_repo = ExecutionRepository(db_session)
    task_repo = TaskRepository(db_session)
    attempt_repo = TaskAttemptRepository(db_session)
    approval_repo = ApprovalRepository(db_session)
    event_repo = ExecutionEventRepository(db_session)
    emitter = EventEmitter(event_repo)
    db_lock = asyncio.Lock()

    executor = AgentExecutor(
        router=CapabilityRouter(),
        agent_registry=agent_registry,
        binding_resolver=BindingResolver(),
        retry_policy=RetryPolicy(),
        approval_policy=ApprovalPolicy(),
        task_repo=task_repo,
        attempt_repo=attempt_repo,
        approval_repo=approval_repo,
        emitter=emitter,
        db_lock=db_lock,
    )
    scheduler = DependencyScheduler(
        execution_repo=execution_repo,
        task_repo=task_repo,
        executor=executor,
        emitter=emitter,
        catalogue=catalogue,
        profile=profile,
        base_context={"user_id": USER_ID, "preferred_cuisines": profile.food_preferences.cuisines},
        db_lock=db_lock,
    )
    return scheduler, execution_repo, task_repo, approval_repo, event_repo


def _healthy_catalogue():
    """The real seed catalogue, but with external-openclaw-personal fully
    enabled/approved/healthy/configured — simulating "if it were configured".
    external-browser-use is left as seeded (already enabled+approved)."""

    catalogue = build_agent_catalogue()
    updated = []
    for agent in catalogue:
        if agent.agent_id == "external-openclaw-personal":
            agent = agent.model_copy(
                update={
                    "enabled": True,
                    "trust_status": AgentTrustStatus.APPROVED,
                    "health_status": AgentHealthStatus.HEALTHY,
                    "implementation_status": AgentImplementationStatus.CONFIGURED,
                }
            )
        updated.append(agent)
    return updated


async def _make_registry(db_session, inject_failure: bool = False):
    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db_session),
        entity_repo=EntityRepository(db_session),
        embedding_service=FakeEmbeddingService(),
        settings=Settings(database_url="sqlite+aiosqlite:///:memory:"),
    )
    return {
        "internal-context-intelligence": ContextIntelligenceAgent(retriever),
        "internal-planning-decision": PlanningDecisionAgent(planner=FakePlanner()),
        "external-browser-use": FakeVenueDiscoveryAgent(),
        "external-openclaw-personal": FakeCalendarAgent(
            ExternalActionRecordRepository(db_session), inject_failure=inject_failure
        ),
    }


async def _create_execution_with_plan(db_session, execution_repo, task_repo):
    execution = await execution_repo.create(USER_ID, "Arrange dinner with Maya tomorrow")
    workflow_version_repo = WorkflowVersionRepository(db_session)
    version = await workflow_version_repo.create(execution.execution_id, DINNER_WORKFLOW_PLAN)
    await task_repo.create_from_workflow(
        execution.execution_id, version.workflow_version_id, DINNER_WORKFLOW_PLAN
    )
    await db_session.commit()
    return execution


async def test_workflow_reaches_waiting_for_approval(db_session) -> None:

    catalogue = _healthy_catalogue()
    profile = build_profile()
    registry = await _make_registry(db_session)
    scheduler, execution_repo, task_repo, approval_repo, event_repo = await _build_scheduler(
        db_session, catalogue, profile, registry
    )

    execution = await _create_execution_with_plan(db_session, execution_repo, task_repo)
    await scheduler.run(execution.execution_id, DINNER_WORKFLOW_PLAN)
    await db_session.commit()

    updated = await execution_repo.get(execution.execution_id)
    assert updated is not None
    assert updated.status == ExecutionStatus.WAITING_FOR_APPROVAL

    tasks = await task_repo.get_by_execution(execution.execution_id)
    create_event_task = next(t for t in tasks if t.task_id == "create_event")
    assert create_event_task.status == TaskStatus.WAITING_FOR_APPROVAL

    proposal = await approval_repo.get_latest_for_task("create_event")
    assert proposal is not None
    assert proposal.status == ApprovalStatus.PENDING

    discover = next(t for t in tasks if t.task_id == "discover_venues")
    calendar = next(t for t in tasks if t.task_id == "check_calendar")
    assert discover.status == TaskStatus.SUCCEEDED
    assert calendar.status == TaskStatus.SUCCEEDED

    events = await event_repo.list_by_execution(execution.execution_id)
    event_types = {e.event_type for e in events}
    assert "approval.requested" in event_types
    assert "task.succeeded" in event_types


async def test_approval_resumes_workflow_to_completed(db_session) -> None:
    catalogue = _healthy_catalogue()

    profile = build_profile()
    registry = await _make_registry(db_session)
    scheduler, execution_repo, task_repo, approval_repo, event_repo = await _build_scheduler(
        db_session, catalogue, profile, registry
    )

    execution = await _create_execution_with_plan(db_session, execution_repo, task_repo)
    await scheduler.run(execution.execution_id, DINNER_WORKFLOW_PLAN)
    await db_session.commit()

    proposal = await approval_repo.get_latest_for_task("create_event")
    assert proposal is not None
    await approval_repo.update_status(proposal.proposal_id, ApprovalStatus.APPROVED)
    await db_session.commit()

    await scheduler.resume_after_approval(execution.execution_id, DINNER_WORKFLOW_PLAN)
    await db_session.commit()

    updated = await execution_repo.get(execution.execution_id)
    assert updated is not None
    assert updated.status == ExecutionStatus.COMPLETED

    tasks = await task_repo.get_by_execution(execution.execution_id)
    assert all(t.status == TaskStatus.SUCCEEDED for t in tasks)

    create_event_task = next(t for t in tasks if t.task_id == "create_event")
    assert create_event_task.output is not None
    assert "event_id" in create_event_task.output

    events = await event_repo.list_by_execution(execution.execution_id)
    event_types = [e.event_type for e in events]
    assert "execution.resumed" in event_types
    assert "execution.completed" in event_types


async def test_venue_discovery_falls_back_when_primary_agent_unavailable(db_session) -> None:
    """Failure/recovery scenario: primary venue agent fails, retry policy
    detects AGENT_UNAVAILABLE, router falls back — but our catalogue has no
    second agent for web.discover_places, so this proves the *fallback path
    is exercised* (NoEligibleAgentError surfaces the original failure)."""
    from synapse_plane.agents.errors import AgentUnavailableError

    class FailingVenueAgent(BaseAgent):
        agent_id = "external-browser-use"

        async def execute(self, agent_input: AgentInput) -> AgentOutput:  # noqa: ARG002
            raise AgentUnavailableError(self.agent_id, "simulated outage")

        def health_check(self) -> bool:
            return False

    catalogue = _healthy_catalogue()
    profile = build_profile()
    registry = await _make_registry(db_session)
    registry["external-browser-use"] = FailingVenueAgent()
    scheduler, execution_repo, task_repo, approval_repo, event_repo = await _build_scheduler(
        db_session, catalogue, profile, registry
    )

    execution = await _create_execution_with_plan(db_session, execution_repo, task_repo)
    await scheduler.run(execution.execution_id, DINNER_WORKFLOW_PLAN)
    await db_session.commit()

    tasks = await task_repo.get_by_execution(execution.execution_id)
    discover = next(t for t in tasks if t.task_id == "discover_venues")
    assert discover.status == TaskStatus.FAILED

    recommend = next(t for t in tasks if t.task_id == "recommend")
    assert recommend.status == TaskStatus.BLOCKED

    updated = await execution_repo.get(execution.execution_id)
    assert updated is not None
    assert updated.status == ExecutionStatus.FAILED

    events = await event_repo.list_by_execution(execution.execution_id)
    event_types = [e.event_type for e in events]
    assert "task.failed" in event_types
