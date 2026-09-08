"""Unit tests for the real-integration adapters — Fake search/LLM/calendar
clients only. No network calls (Tavily, Gemini, Google are never hit)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from synapse_plane.agents.base import AgentInput
from synapse_plane.agents.external.browser_use_adapter import BrowserUseAdapter
from synapse_plane.agents.external.open_deep_research_adapter import OpenDeepResearchAdapter
from synapse_plane.agents.external.openclaw_adapter import OpenClawAdapter
from synapse_plane.domain.tools import CalendarEventResult, TimeSlot, WebSearchResult
from synapse_plane.tools.search_client import FakeSearchClient


class FakeLLMClient:
    """Minimal stand-in for AsyncOpenAI's chat.completions.create — no network."""

    def __init__(self, response_content: str):
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._response_content = response_content

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._response_content))]
        )


class FakeCalendarReadTool:
    async def get_availability(self, user_id: str, date: str) -> list[TimeSlot]:  # noqa: ARG002
        now = datetime.now(UTC)
        return [TimeSlot(start_time=now, end_time=now + timedelta(hours=2), is_free=True)]


class FakeCalendarWriteTool:
    def __init__(self):
        self.created: list = []

    async def create_event(self, event, idempotency_key: str) -> CalendarEventResult:  # noqa: ARG002
        result = CalendarEventResult(
            event_id="evt-fake-1",
            title=event.title,
            start_time=event.start_time,
            end_time=event.end_time,
            calendar_id=event.calendar_id,
        )
        self.created.append(result)
        return result


async def test_browser_use_health_check_true_when_configured() -> None:
    adapter = BrowserUseAdapter(search_client=FakeSearchClient(), llm_client=FakeLLMClient("{}"))
    assert adapter.health_check() is True


async def test_browser_use_extracts_candidates_from_search_results() -> None:
    search_client = FakeSearchClient(
        canned={
            "restaurants in colombo": [
                WebSearchResult(
                    title="La Foresta Colombo",
                    url="https://example.com/la-foresta",
                    content="A quiet, cozy Italian restaurant on Flower Road.",
                )
            ]
        }
    )
    llm_client = FakeLLMClient(
        '{"restaurants": [{"name": "La Foresta", "address": "Flower Road", '
        '"cuisine": "italian", "rating": 4.6, "price_level": "moderate", '
        '"is_quiet": true, "distance_km": 2.0}]}'
    )
    adapter = BrowserUseAdapter(search_client=search_client, llm_client=llm_client)

    output = await adapter.execute(
        AgentInput(
            goal="find restaurants",
            task_id="t1",
            execution_id="e1",
            context={"location": "Colombo", "requirements": "quiet italian"},
        )
    )

    assert output.success is True
    assert len(output.result["candidates"]) == 1
    assert output.result["candidates"][0]["name"] == "La Foresta"
    assert "colombo" in search_client.queries_seen[0].lower()


async def test_browser_use_skips_malformed_llm_output() -> None:
    search_client = FakeSearchClient()
    llm_client = FakeLLMClient('{"restaurants": [{"name": "Missing Fields Only"}]}')
    adapter = BrowserUseAdapter(search_client=search_client, llm_client=llm_client)

    output = await adapter.execute(
        AgentInput(goal="find restaurants", task_id="t1", execution_id="e1", context={})
    )

    assert output.result["candidates"] == []
    assert output.confidence < 0.5


async def test_open_deep_research_health_check_true_when_configured() -> None:
    adapter = OpenDeepResearchAdapter(
        search_client=FakeSearchClient(), llm_client=FakeLLMClient("{}")
    )
    assert adapter.health_check() is True


async def test_open_deep_research_synthesizes_report() -> None:
    search_client = FakeSearchClient(
        canned={
            "kandy vs galle": [
                WebSearchResult(
                    title="Kandy travel guide",
                    url="https://example.com/kandy",
                    content="Kandy is a hill-country city known for the Temple of the Tooth.",
                )
            ]
        }
    )
    llm_client = FakeLLMClient(
        '{"summary": "Kandy suits history, Galle suits coast.", '
        '"findings": ["Kandy has the Temple of the Tooth"], '
        '"sources": ["https://example.com/kandy"]}'
    )
    adapter = OpenDeepResearchAdapter(search_client=search_client, llm_client=llm_client)

    output = await adapter.execute(
        AgentInput(
            goal="Compare Kandy vs Galle for a trip",
            task_id="t1",
            execution_id="e1",
            context={},
        )
    )

    assert output.success is True
    assert "summary" in output.result
    assert len(output.result["findings"]) == 1


async def test_openclaw_health_check_true_when_configured() -> None:
    adapter = OpenClawAdapter(read_tool=FakeCalendarReadTool(), write_tool=FakeCalendarWriteTool())
    assert adapter.health_check() is True


async def test_openclaw_checks_availability() -> None:
    adapter = OpenClawAdapter(read_tool=FakeCalendarReadTool(), write_tool=FakeCalendarWriteTool())

    output = await adapter.execute(
        AgentInput(
            goal="check calendar",
            task_id="check_calendar",
            execution_id="e1",
            context={"user_id": "user-1", "date": "2026-09-10"},
            required_capability="personal.calendar_availability",
        )
    )

    assert output.success is True
    assert output.result["is_free"] is True


async def test_openclaw_creates_event() -> None:
    write_tool = FakeCalendarWriteTool()
    adapter = OpenClawAdapter(read_tool=FakeCalendarReadTool(), write_tool=write_tool)
    now = datetime.now(UTC)

    output = await adapter.execute(
        AgentInput(
            goal="create event",
            task_id="create_event",
            execution_id="e1",
            context={
                "recommendation": {"selected": {"name": "La Foresta", "address": "Flower Road"}},
                "availability": {"start_time": now, "end_time": now + timedelta(hours=2)},
            },
            required_capability="personal.calendar_create",
        )
    )

    assert output.success is True
    assert output.result["event_id"] == "evt-fake-1"
    assert len(write_tool.created) == 1
