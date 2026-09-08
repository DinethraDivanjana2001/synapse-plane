"""Tests for GoogleCalendarTool — a fake Calendar service stands in for the
real googleapiclient resource. No network calls, no real Google API touched."""

from datetime import UTC, datetime, timedelta

import pytest

from synapse_plane.domain.tools import CalendarEventRequest
from synapse_plane.persistence.repositories import ExternalActionRecordRepository
from synapse_plane.tools.google_calendar_tool import (
    GoogleCalendarAuthRequiredError,
    GoogleCalendarTool,
    load_google_calendar_credentials,
)


class _FakeExecutable:
    def __init__(self, result: dict):
        self._result = result

    def execute(self) -> dict:
        return self._result


class FakeGoogleCalendarService:
    """Fake for GoogleCalendarServiceProtocol — no network, no filesystem."""

    def __init__(self, busy_blocks: list[dict] | None = None, event_id: str = "google-evt-fake-1"):
        self._busy_blocks = busy_blocks or []
        self._event_id = event_id

    def freebusy(self):
        return self

    def query(self, body: dict):  # noqa: ARG002
        return _FakeExecutable({"calendars": {"primary": {"busy": self._busy_blocks}}})

    def events(self):
        return self

    def insert(self, calendarId: str, body: dict):  # noqa: ARG002, N803
        return _FakeExecutable({"id": self._event_id})


async def test_get_availability_free_when_no_conflicts() -> None:
    tool = GoogleCalendarTool(FakeGoogleCalendarService(busy_blocks=[]), action_repo=None)  # type: ignore[arg-type]

    slots = await tool.get_availability("user-1", "2026-09-10")

    assert slots[0].is_free is True


async def test_get_availability_busy_when_conflict_overlaps() -> None:
    service = FakeGoogleCalendarService(
        busy_blocks=[{"start": "2026-09-10T19:30:00+00:00", "end": "2026-09-10T20:30:00+00:00"}]
    )
    tool = GoogleCalendarTool(service, action_repo=None)  # type: ignore[arg-type]

    slots = await tool.get_availability("user-1", "2026-09-10")

    assert slots[0].is_free is False


async def test_create_event_is_idempotent(db_session) -> None:
    service = FakeGoogleCalendarService()
    tool = GoogleCalendarTool(service, ExternalActionRecordRepository(db_session))
    now = datetime.now(UTC)
    request = CalendarEventRequest(
        title="Dinner with Maya",
        start_time=now,
        end_time=now + timedelta(hours=2),
        calendar_id="primary",
    )

    first = await tool.create_event(request, idempotency_key="exec-1:task-1:1")
    await db_session.commit()
    second = await tool.create_event(request, idempotency_key="exec-1:task-1:1")
    await db_session.commit()

    assert first.event_id == second.event_id == "google-evt-fake-1"


def test_load_credentials_raises_when_token_missing(tmp_path) -> None:
    missing_token_path = str(tmp_path / "nonexistent_token.json")
    with pytest.raises(GoogleCalendarAuthRequiredError):
        load_google_calendar_credentials(missing_token_path)
