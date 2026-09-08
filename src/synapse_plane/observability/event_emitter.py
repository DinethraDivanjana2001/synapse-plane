"""Emits structured events into an execution's audit timeline."""

from datetime import UTC, datetime
from uuid import uuid4

from synapse_plane.domain.execution import ExecutionEvent
from synapse_plane.persistence.execution_repositories import ExecutionEventRepository


# Records every significant orchestration action for the timeline/audit trail
class EventEmitter:
    def __init__(self, event_repo: ExecutionEventRepository):
        self.event_repo = event_repo

    async def emit(
        self,
        execution_id: str,
        event_type: str,
        task_id: str | None = None,
        agent_id: str | None = None,
        attempt_id: str | None = None,
        **payload: object,
    ) -> None:
        event = ExecutionEvent(
            event_id=str(uuid4()),
            execution_id=execution_id,
            event_type=event_type,
            task_id=task_id,
            agent_id=agent_id,
            attempt_id=attempt_id,
            payload=payload,
            occurred_at=datetime.now(UTC),
        )
        await self.event_repo.create(event)
