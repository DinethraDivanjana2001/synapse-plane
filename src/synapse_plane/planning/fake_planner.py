"""Deterministic planner — no LLM calls. Used in all tests and the demo."""

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import RiskLevel
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.workflow import TaskDefinition, WorkflowDefinition
from synapse_plane.planning.errors import UnsupportedCapabilityError

_PROHIBITED_KEYWORDS = ("flight", "book a ticket", "buy ticket", "payment", "hotel")

# Use Case 1: dinner planning — context -> venues/calendar (parallel) -> recommend -> create event
DINNER_WORKFLOW_PLAN = WorkflowDefinition(
    workflow_id="demo-dinner-plan",
    goal="Arrange dinner and create a calendar event",
    tasks=[
        TaskDefinition(
            task_id="resolve_context",
            task_type="agent_task",
            description="Retrieve grounded context relevant to this intent",
            required_capability="context.retrieve",
            depends_on=[],
            input_bindings={},
            output_schema="ContextPackage@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="discover_venues",
            task_type="agent_task",
            description="Discover candidate restaurants matching preferences",
            required_capability="web.discover_places",
            depends_on=["resolve_context"],
            input_bindings={"context": "$tasks.resolve_context.output"},
            output_schema="VenueCandidateList@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="check_calendar",
            task_type="agent_task",
            description="Check calendar availability",
            required_capability="personal.calendar_availability",
            depends_on=["resolve_context"],
            input_bindings={"context": "$tasks.resolve_context.output"},
            output_schema="AvailabilityWindow@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="recommend",
            task_type="agent_task",
            description="Rank venues and synthesize a recommendation",
            required_capability="recommendation.synthesize",
            depends_on=["discover_venues", "check_calendar"],
            input_bindings={
                "venues": "$tasks.discover_venues.output",
                "availability": "$tasks.check_calendar.output",
            },
            output_schema="Recommendation@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="create_event",
            task_type="agent_task",
            description="Create the calendar event for the chosen venue",
            required_capability="personal.calendar_create",
            depends_on=["recommend"],
            input_bindings={"recommendation": "$tasks.recommend.output"},
            output_schema="CalendarEventResult@1",
            risk_level=RiskLevel.CONSEQUENTIAL_WRITE,
            approval_required=True,
        ),
    ],
)

# Use Case 2: travel research — context -> open-deep-research + browser-use (parallel) -> compare
TRAVEL_WORKFLOW_PLAN = WorkflowDefinition(
    workflow_id="demo-travel-plan",
    goal="Compare travel destinations and recommend one",
    tasks=[
        TaskDefinition(
            task_id="resolve_context",
            task_type="agent_task",
            description="Retrieve grounded context relevant to this intent",
            required_capability="context.retrieve",
            depends_on=[],
            input_bindings={},
            output_schema="ContextPackage@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="research_destinations",
            task_type="agent_task",
            description="Deep multi-source research on candidate destinations",
            required_capability="research.deep",
            depends_on=["resolve_context"],
            input_bindings={"context": "$tasks.resolve_context.output"},
            output_schema="ResearchReport@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="verify_details",
            task_type="agent_task",
            description="Verify practical, current details on candidate destinations",
            required_capability="web.verify_information",
            depends_on=["resolve_context"],
            input_bindings={"context": "$tasks.resolve_context.output"},
            output_schema="VerifiedDetails@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
        TaskDefinition(
            task_id="compare_options",
            task_type="agent_task",
            description="Compare destinations and recommend one",
            required_capability="alternatives.compare",
            depends_on=["research_destinations", "verify_details"],
            input_bindings={
                "research": "$tasks.research_destinations.output",
                "details": "$tasks.verify_details.output",
            },
            output_schema="Recommendation@1",
            risk_level=RiskLevel.READ_ONLY,
            approval_required=False,
        ),
    ],
)

_TRAVEL_KEYWORDS = ("trip", "travel", "destination", "kandy", "galle", "vacation")


class FakePlanner:
    async def plan(
        self, intent: str, _profile: UserProfile, _catalogue: list[AgentManifest]
    ) -> WorkflowDefinition:
        lowered = intent.lower()
        if any(k in lowered for k in _PROHIBITED_KEYWORDS):
            raise UnsupportedCapabilityError(["flight.book", "payment.execute"])
        if any(k in lowered for k in _TRAVEL_KEYWORDS):
            return TRAVEL_WORKFLOW_PLAN
        return DINNER_WORKFLOW_PLAN
