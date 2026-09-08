"""Personal assistant agent for calendar actions.

No real OpenClaw MCP gateway is running in this environment. Instead of
pretending one exists, this adapter calls calendar tools directly — inject
GoogleCalendarTool for the real Google Calendar API, or the mock
CalendarReadTool/CalendarWriteTool for tests/demo. Both expose the same
method shapes, so this class doesn't need to know which one it holds.
"""

from typing import Protocol

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError
from synapse_plane.domain.tools import CalendarEventRequest, CalendarEventResult, TimeSlot


class CalendarReadToolProtocol(Protocol):
    async def get_availability(self, user_id: str, date: str) -> list[TimeSlot]: ...


class CalendarWriteToolProtocol(Protocol):
    async def create_event(
        self, event: CalendarEventRequest, idempotency_key: str
    ) -> CalendarEventResult: ...


# Personal-assistant agent for calendar read/write, backed by whichever
# calendar tool (mock or real Google) it's constructed with
class OpenClawAdapter(BaseAgent):
    agent_id = "external-openclaw-personal"

    def __init__(
        self,
        read_tool: CalendarReadToolProtocol | None = None,
        write_tool: CalendarWriteToolProtocol | None = None,
    ):
        self.read_tool = read_tool
        self.write_tool = write_tool

    def health_check(self) -> bool:
        return self.read_tool is not None and self.write_tool is not None

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not self.health_check():
            raise AgentUnavailableError(self.agent_id, "no calendar tool configured")

        if agent_input.required_capability == "personal.calendar_create":
            return await self._create_event(agent_input)
        return await self._check_availability(agent_input)

    async def _check_availability(self, agent_input: AgentInput) -> AgentOutput:
        user_id = agent_input.context.get("user_id", "")
        date = agent_input.context.get("date", "2026-09-10")
        slots = await self.read_tool.get_availability(user_id, date)  # type: ignore[union-attr]
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=slots[0].model_dump(mode="json") if slots else {},
            observations=[f"Checked calendar availability for {date}"],
            tool_calls_made=["calendar_read"],
            confidence=0.9,
        )

    async def _create_event(self, agent_input: AgentInput) -> AgentOutput:
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
        result = await self.write_tool.create_event(request, idempotency_key)  # type: ignore[union-attr]

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=result.model_dump(mode="json"),
            observations=[f"Created calendar event {result.event_id}"],
            tool_calls_made=["calendar_write"],
            confidence=0.95,
        )
