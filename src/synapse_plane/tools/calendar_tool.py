"""Calendar tools — mock provider, real idempotency enforcement."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

from synapse_plane.domain.tools import CalendarEventRequest, CalendarEventResult, TimeSlot
from synapse_plane.persistence.repositories import ExternalActionRecordRepository
from synapse_plane.planning.intent_context import MEAL_HOURS

# The single demo profile's timezone (demo/seed.py): Asia/Colombo, a fixed
# UTC+5:30 offset with no DST — a plain fixed-offset timezone is exact here
# and avoids depending on the IANA tzdata package (not bundled with Python on
# Windows; ZoneInfo("Asia/Colombo") raises ZoneInfoNotFoundError without it).
# "7pm" below means 7pm here, not 7pm UTC — storing it naively as UTC (the
# previous bug) made the proposal's displayed time drift by the UTC offset
# for any viewer not in this timezone (confirmed: showed as 12:30-2:30 AM
# for a Colombo viewer, since the browser correctly converts UTC to local).
_DEMO_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

# Kept for backwards compatibility with anything still importing the old
# dinner-only name; MEAL_HOURS["dinner"] is the same tuple.
DINNER_START_HOURS = MEAL_HOURS["dinner"]
SLOT_DURATION_HOURS = 2

# Mock provider only: one canned commitment per meal so the free/busy
# distinction is visible without a real calendar behind it.
_MOCK_BUSY_HOURS = {8, 13, 18}


def evening_slot_bounds(date: str, hour: int) -> tuple[datetime, datetime]:
    """A local-time slot for `date` starting at `hour`, as UTC-aware bounds."""
    local_midnight = datetime.fromisoformat(date).replace(tzinfo=_DEMO_TIMEZONE)
    start = local_midnight.replace(hour=hour, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=SLOT_DURATION_HOURS)
    return start.astimezone(UTC), end.astimezone(UTC)


def choose_slot(slots: list[TimeSlot], preferred_time: str | None = None) -> TimeSlot | None:
    """Prefer the user's requested hour if it's free, else the earliest free
    slot. Never silently returns a busy slot unless every slot is busy."""
    free = [s for s in slots if s.is_free]
    if preferred_time:
        wanted = preferred_time.strip()[:2]
        for slot in free:
            if slot.start_time.astimezone(_DEMO_TIMEZONE).strftime("%H") == wanted.zfill(2):
                return slot
    if free:
        return free[0]
    return slots[0] if slots else None


# Reads calendar availability — one operation, no reasoning
class CalendarReadTool:
    async def get_availability(
        self,
        user_id: str,  # noqa: ARG002
        date: str,
        meal: str = "dinner",
    ) -> list[TimeSlot]:
        slots = []
        for hour in MEAL_HOURS.get(meal, MEAL_HOURS["dinner"]):
            start, end = evening_slot_bounds(date, hour)
            slots.append(
                TimeSlot(start_time=start, end_time=end, is_free=hour not in _MOCK_BUSY_HOURS)
            )
        return slots


# Creates a calendar event exactly once per idempotency key
class CalendarWriteTool:
    def __init__(self, action_repo: ExternalActionRecordRepository):
        self.action_repo = action_repo

    async def create_event(
        self, event: CalendarEventRequest, idempotency_key: str
    ) -> CalendarEventResult:
        existing = await self.action_repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return CalendarEventResult.model_validate_json(existing.result_json)

        result = CalendarEventResult(
            event_id=f"evt-{uuid4()}",
            title=event.title,
            start_time=event.start_time,
            end_time=event.end_time,
            calendar_id=event.calendar_id,
        )
        await self.action_repo.create(
            idempotency_key=idempotency_key,
            provider="mock_calendar",
            provider_reference_id=result.event_id,
            result_json=result.model_dump_json(),
        )
        return result
