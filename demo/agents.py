"""Deterministic demo/test stand-in agents — used whenever DEMO_MODE=true
(the .env default) and by every scenario test. Never touch a network.

DemoVenueDiscoveryAgent demonstrates tool-level resilience (PlacesTool ->
PlacesFallbackTool) inside a single agent: v3's catalogue has exactly one
agent for web.discover_places, so the "primary fails -> fallback -> success"
scenario is agent-internal here, not agent-selection-level.
"""

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.domain.tools import CalendarEventRequest, RestaurantSearchRequest
from synapse_plane.persistence.repositories import ExternalActionRecordRepository
from synapse_plane.tools.calendar_tool import CalendarReadTool, CalendarWriteTool
from synapse_plane.tools.errors import ToolTimeoutError
from synapse_plane.tools.places_tool import PlacesFallbackTool, PlacesTool


# Stand-in for external-browser-use — PlacesTool with PlacesFallbackTool resilience
class DemoVenueDiscoveryAgent(BaseAgent):
    agent_id = "external-browser-use"

    def __init__(self, inject_failure: bool = False):
        self.primary = PlacesTool()
        self.fallback = PlacesFallbackTool()
        self.inject_failure = inject_failure

    def health_check(self) -> bool:
        return True

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        request = RestaurantSearchRequest(
            location_label=agent_input.context.get("location", "Colombo")
        )
        tool_calls = []
        try:
            candidates = await self.primary.search(request, inject_failure=self.inject_failure)
            tool_calls.append("places_primary_tool")
        except ToolTimeoutError:
            candidates = await self.fallback.search(request)
            tool_calls.append("places_fallback_tool")

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={"candidates": [c.model_dump(mode="json") for c in candidates]},
            observations=[f"Found {len(candidates)} venues via {tool_calls[-1]}"],
            tool_calls_made=tool_calls,
            confidence=0.85,
        )


# Stand-in for external-openclaw-personal — mock calendar tools
class DemoCalendarAgent(BaseAgent):
    agent_id = "external-openclaw-personal"

    def __init__(self, action_repo: ExternalActionRecordRepository):
        self.read_tool = CalendarReadTool()
        self.write_tool = CalendarWriteTool(action_repo)

    def health_check(self) -> bool:
        return True

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
                description=f"Arranged via SynapsePlane — {selected.get('address', '')}",
            )
            idempotency_key = f"{agent_input.execution_id}:{agent_input.task_id}:1"
            result = await self.write_tool.create_event(request, idempotency_key)
            return AgentOutput(
                task_id=agent_input.task_id,
                agent_id=self.agent_id,
                success=True,
                result=result.model_dump(mode="json"),
                observations=[f"Created calendar event {result.event_id}"],
                tool_calls_made=["calendar_write_tool"],
                confidence=0.95,
            )

        user_id = agent_input.context.get("user_id", "")
        date = agent_input.context.get("date", "2026-09-10")
        slots = await self.read_tool.get_availability(user_id, date)
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=slots[0].model_dump(mode="json") if slots else {},
            observations=[f"Checked calendar availability for {date}"],
            tool_calls_made=["calendar_read_tool"],
            confidence=0.9,
        )
