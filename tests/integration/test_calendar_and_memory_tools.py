"""Integration tests for CalendarWriteTool and MemoryStoreTool — real DB."""

from datetime import UTC, datetime, timedelta

from synapse_plane.domain.tools import CalendarEventRequest
from synapse_plane.memory.embedding_service import FakeEmbeddingService
from synapse_plane.persistence.repositories import ExternalActionRecordRepository, MemoryRepository
from synapse_plane.tools.calendar_tool import CalendarReadTool, CalendarWriteTool
from synapse_plane.tools.memory_tool import MemoryStoreTool


async def test_get_availability_returns_a_slot() -> None:
    slots = await CalendarReadTool().get_availability("user-1", "2026-09-10")
    assert len(slots) == 1
    assert slots[0].is_free is True


async def test_create_event_is_idempotent(db_session) -> None:
    tool = CalendarWriteTool(ExternalActionRecordRepository(db_session))
    now = datetime.now(UTC)
    request = CalendarEventRequest(
        title="Dinner with Maya",
        start_time=now,
        end_time=now + timedelta(hours=2),
        calendar_id="primary",
    )

    first = await tool.create_event(request, idempotency_key="exec-1:task-1:v1")
    await db_session.commit()
    second = await tool.create_event(request, idempotency_key="exec-1:task-1:v1")
    await db_session.commit()

    assert first.event_id == second.event_id


async def test_record_outcome_creates_a_memory(db_session) -> None:
    tool = MemoryStoreTool(MemoryRepository(db_session), FakeEmbeddingService())

    memory = await tool.record_outcome("user-1", "Chose La Foresta for dinner with Maya")
    await db_session.commit()

    stored = await MemoryRepository(db_session).list_by_user("user-1")
    assert len(stored) == 1
    assert stored[0].memory_id == memory.memory_id
    assert stored[0].memory_type.value == "outcome"
