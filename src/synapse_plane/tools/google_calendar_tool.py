"""Real Google Calendar integration (OAuth 'installed app' flow).

This module never runs the interactive consent screen itself — it only
loads/refreshes an already-cached token. The first-ever authorization is a
one-time interactive step the operator runs locally:
    python scripts/setup_google_calendar_auth.py
"""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from synapse_plane.domain.tools import CalendarEventRequest, CalendarEventResult, TimeSlot
from synapse_plane.persistence.repositories import ExternalActionRecordRepository
from synapse_plane.planning.intent_context import MEAL_HOURS
from synapse_plane.tools.calendar_tool import SLOT_DURATION_HOURS, evening_slot_bounds

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Same fixed-offset fix as tools/calendar_tool.py's mock CalendarReadTool: the
# single demo profile is Asia/Colombo (UTC+5:30, no DST). "7pm" means 7pm
# there, not 7pm UTC — treating it as UTC would query Google's freebusy API
# for the wrong window and, worse, create the real calendar event 5.5 hours
# off from the intended time.
_DEMO_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


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

    async def get_availability(
        self,
        user_id: str,  # noqa: ARG002
        date: str,
        meal: str = "dinner",
    ) -> list[TimeSlot]:
        """Every candidate slot for the requested meal, each marked free or
        busy against the real calendar — the caller picks; this tool only
        reports."""
        hours = MEAL_HOURS.get(meal, MEAL_HOURS["dinner"])
        local_day = datetime.fromisoformat(date).replace(tzinfo=_DEMO_TIMEZONE)
        window_start = local_day.replace(hour=hours[0], minute=0, second=0)
        window_end = local_day.replace(hour=hours[-1], minute=0, second=0) + timedelta(
            hours=SLOT_DURATION_HOURS
        )

        body = {
            "timeMin": window_start.astimezone(UTC).isoformat(),
            "timeMax": window_end.astimezone(UTC).isoformat(),
            "items": [{"id": self.calendar_id}],
        }
        response = await asyncio.to_thread(
            lambda: self.service.freebusy().query(body=body).execute()
        )
        busy = response["calendars"][self.calendar_id]["busy"]

        slots = []
        for hour in hours:
            start, end = evening_slot_bounds(date, hour)
            overlaps = any(
                datetime.fromisoformat(b["start"]) < end
                and datetime.fromisoformat(b["end"]) > start
                for b in busy
            )
            slots.append(TimeSlot(start_time=start, end_time=end, is_free=not overlaps))
        return slots

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
