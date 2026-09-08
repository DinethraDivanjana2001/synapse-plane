"""Real Google Calendar integration (OAuth 'installed app' flow).

This module never runs the interactive consent screen itself — it only
loads/refreshes an already-cached token. The first-ever authorization is a
one-time interactive step the operator runs locally:
    python scripts/setup_google_calendar_auth.py
"""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from synapse_plane.domain.tools import CalendarEventRequest, CalendarEventResult, TimeSlot
from synapse_plane.persistence.repositories import ExternalActionRecordRepository

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarAuthRequiredError(Exception):
    def __init__(self, token_path: str):
        self.token_path = token_path
        super().__init__(
            f"No valid Google Calendar token at '{token_path}'. Run "
            "`python scripts/setup_google_calendar_auth.py` once, interactively, first."
        )


class GoogleCalendarServiceProtocol(Protocol):
    """Subset of the googleapiclient Calendar resource this tool uses —
    lets tests inject a fake without touching Google or the filesystem."""

    def freebusy(self) -> Any: ...
    def events(self) -> Any: ...


def load_google_calendar_credentials(token_path: str):  # type: ignore[no-untyped-def]
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    path = Path(token_path)
    if not path.exists():
        raise GoogleCalendarAuthRequiredError(token_path)

    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    if not creds.valid:
        raise GoogleCalendarAuthRequiredError(token_path)
    return creds


def build_google_calendar_service(token_path: str) -> GoogleCalendarServiceProtocol:
    from googleapiclient.discovery import build

    creds = load_google_calendar_credentials(token_path)
    return build("calendar", "v3", credentials=creds)


# Real Google Calendar reads/writes — same method shapes as CalendarReadTool/
# CalendarWriteTool so OpenClawAdapter can hold either without changing code.
class GoogleCalendarTool:
    def __init__(
        self,
        service: GoogleCalendarServiceProtocol,
        action_repo: ExternalActionRecordRepository,
        calendar_id: str = "primary",
    ):
        self.service = service
        self.action_repo = action_repo
        self.calendar_id = calendar_id

    async def get_availability(self, user_id: str, date: str) -> list[TimeSlot]:  # noqa: ARG002
        day = datetime.fromisoformat(date).replace(tzinfo=UTC)
        window_start = day.replace(hour=9, minute=0, second=0, microsecond=0)
        window_end = day.replace(hour=21, minute=0, second=0, microsecond=0)

        body = {
            "timeMin": window_start.isoformat(),
            "timeMax": window_end.isoformat(),
            "items": [{"id": self.calendar_id}],
        }
        response = await asyncio.to_thread(
            lambda: self.service.freebusy().query(body=body).execute()
        )
        busy = response["calendars"][self.calendar_id]["busy"]

        candidate_start = day.replace(hour=19, minute=0, second=0, microsecond=0)
        candidate_end = candidate_start + timedelta(hours=2)
        is_free = not any(
            datetime.fromisoformat(b["start"]) < candidate_end
            and datetime.fromisoformat(b["end"]) > candidate_start
            for b in busy
        )
        return [TimeSlot(start_time=candidate_start, end_time=candidate_end, is_free=is_free)]

    async def create_event(
        self, event: CalendarEventRequest, idempotency_key: str
    ) -> CalendarEventResult:
        existing = await self.action_repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return CalendarEventResult.model_validate_json(existing.result_json)

        body = {
            "summary": event.title,
            "description": event.description,
            "start": {"dateTime": event.start_time.isoformat()},
            "end": {"dateTime": event.end_time.isoformat()},
        }
        created = await asyncio.to_thread(
            lambda: self.service.events().insert(calendarId=self.calendar_id, body=body).execute()
        )

        result = CalendarEventResult(
            event_id=created["id"],
            title=event.title,
            start_time=event.start_time,
            end_time=event.end_time,
            calendar_id=self.calendar_id,
        )
        await self.action_repo.create(
            idempotency_key=idempotency_key,
            provider="google_calendar",
            provider_reference_id=result.event_id,
            result_json=result.model_dump_json(),
        )
        return result
