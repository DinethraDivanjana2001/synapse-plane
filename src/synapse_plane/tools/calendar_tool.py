"""Calendar tools — mock provider, real idempotency enforcement."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from synapse_plane.domain.tools import CalendarEventRequest, CalendarEventResult, TimeSlot
from synapse_plane.persistence.repositories import ExternalActionRecordRepository


# Reads calendar availability — one operation, no reasoning
class CalendarReadTool:
    async def get_availability(self, user_id: str, date: str) -> list[TimeSlot]:  # noqa: ARG002
        day_start = datetime.fromisoformat(date).replace(tzinfo=UTC)
        evening = day_start + timedelta(hours=19)
        return [TimeSlot(start_time=evening, end_time=evening + timedelta(hours=2), is_free=True)]


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
