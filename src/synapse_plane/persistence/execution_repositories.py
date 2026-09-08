"""Repositories for the execution/task/approval/event tables."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from synapse_plane.domain.enums import ApprovalStatus, AttemptStatus, ExecutionStatus, TaskStatus
from synapse_plane.domain.execution import (
    ApprovalProposal,
    Execution,
    ExecutionEvent,
    Task,
    TaskAttempt,
    WorkflowVersionRecord,
)
from synapse_plane.domain.workflow import TaskDefinition, WorkflowDefinition
from synapse_plane.persistence.models import (
    ApprovalModel,
    ExecutionEventModel,
    ExecutionModel,
    TaskAttemptModel,
    TaskDependencyModel,
    TaskModel,
    WorkflowVersionModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


# CRUD for executions
class ExecutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: str, intent_text: str) -> Execution:
        now = _now()
        execution = Execution(
            execution_id=str(uuid4()),
            user_id=user_id,
            intent_text=intent_text,
            status=ExecutionStatus.RECEIVED,
            created_at=now,
            updated_at=now,
        )
        self.session.add(
            ExecutionModel(
                id=execution.execution_id,
                user_id=user_id,
                intent_text=intent_text,
                status=execution.status.value,
                created_at=now,
                updated_at=now,
            )
        )
        await self.session.flush()
        return execution

    async def get(self, execution_id: str) -> Execution | None:
        row = await self.session.get(ExecutionModel, execution_id)
        if row is None:
            return None
        return Execution(
            execution_id=row.id,
            user_id=row.user_id,
            intent_text=row.intent_text,
            status=ExecutionStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def update_status(self, execution_id: str, status: ExecutionStatus) -> None:
        row = await self.session.get(ExecutionModel, execution_id)
        if row is not None:
            row.status = status.value
            row.updated_at = _now()
            await self.session.flush()


# CRUD for workflow versions (one per plan/re-plan)
class WorkflowVersionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, execution_id: str, workflow: WorkflowDefinition
    ) -> WorkflowVersionRecord:
        record = WorkflowVersionRecord(
            workflow_version_id=str(uuid4()),
            execution_id=execution_id,
            planning_version=workflow.planning_version,
            workflow=workflow,
            created_at=_now(),
        )
        self.session.add(
            WorkflowVersionModel(
                id=record.workflow_version_id,
                execution_id=execution_id,
                planning_version=workflow.planning_version,
                workflow_json=workflow.model_dump_json(),
                created_at=record.created_at,
            )
        )
        await self.session.flush()
        return record

    async def get_latest_for_execution(self, execution_id: str) -> WorkflowVersionRecord | None:
        result = await self.session.execute(
            select(WorkflowVersionModel)
            .where(WorkflowVersionModel.execution_id == execution_id)
            .order_by(WorkflowVersionModel.created_at.desc())
        )
        row = result.scalars().first()
        if row is None:
            return None
        return WorkflowVersionRecord(
            workflow_version_id=row.id,
            execution_id=row.execution_id,
            planning_version=row.planning_version,
            workflow=WorkflowDefinition.model_validate_json(row.workflow_json),
            created_at=row.created_at,
        )


def _task_row_id(execution_id: str, task_key: str) -> str:
    """The same fixed plan (FakePlanner) repeats task_keys across
    executions, so the row id must combine both to stay unique."""
    return f"{execution_id}:{task_key}"


def _task_from_row(row: TaskModel) -> Task:
    return Task(
        task_id=row.task_key,
        execution_id=row.execution_id,
        workflow_version_id=row.workflow_version_id,
        definition=TaskDefinition.model_validate_json(row.task_definition_json),
        status=TaskStatus(row.status),
        selected_agent_id=row.selected_agent_id,
        output=json.loads(row.output_json) if row.output_json else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# CRUD for tasks within an execution
class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_from_workflow(
        self, execution_id: str, workflow_version_id: str, workflow: WorkflowDefinition
    ) -> list[Task]:
        now = _now()
        tasks = []
        for task_def in workflow.tasks:
            row = TaskModel(
                id=_task_row_id(execution_id, task_def.task_id),
                execution_id=execution_id,
                workflow_version_id=workflow_version_id,
                task_key=task_def.task_id,
                task_definition_json=task_def.model_dump_json(),
                status=TaskStatus.PENDING.value,
                created_at=now,
                updated_at=now,
            )
            self.session.add(row)
            tasks.append(_task_from_row(row))
        await self.session.flush()

        for task_def in workflow.tasks:
            for dep in task_def.depends_on:
                self.session.add(
                    TaskDependencyModel(
                        id=str(uuid4()),
                        execution_id=execution_id,
                        task_key=task_def.task_id,
                        depends_on_task_key=dep,
                    )
                )
        await self.session.flush()
        return tasks

    async def get_by_execution(self, execution_id: str) -> list[Task]:
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.execution_id == execution_id)
        )
        return [_task_from_row(row) for row in result.scalars().all()]

    async def get(self, execution_id: str, task_key: str) -> Task | None:
        row = await self.session.get(TaskModel, _task_row_id(execution_id, task_key))
        return _task_from_row(row) if row is not None else None

    async def update_status(self, execution_id: str, task_key: str, status: TaskStatus) -> None:
        row = await self.session.get(TaskModel, _task_row_id(execution_id, task_key))
        if row is not None:
            row.status = status.value
            row.updated_at = _now()
            await self.session.flush()

    async def update_output(
        self,
        execution_id: str,
        task_key: str,
        output: dict,
        selected_agent_id: str | None = None,
    ) -> None:
        row = await self.session.get(TaskModel, _task_row_id(execution_id, task_key))
        if row is not None:
            row.output_json = json.dumps(output)
            if selected_agent_id is not None:
                row.selected_agent_id = selected_agent_id
            row.updated_at = _now()
            await self.session.flush()


# CRUD for individual task execution attempts
class TaskAttemptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task_row_id: str, attempt_number: int, agent_id: str) -> TaskAttempt:
        """task_row_id is the tasks.id FK — the composite f"{execution_id}:
        {task_key}" form, not the bare workflow-local task_key."""
        now = _now()
        attempt = TaskAttempt(
            attempt_id=str(uuid4()),
            task_id=task_row_id,
            attempt_number=attempt_number,
            agent_id=agent_id,
            status=AttemptStatus.RUNNING,
            started_at=now,
        )
        self.session.add(
            TaskAttemptModel(
                id=attempt.attempt_id,
                task_id=task_row_id,
                attempt_number=attempt_number,
                agent_id=agent_id,
                status=AttemptStatus.RUNNING.value,
                started_at=now,
            )
        )
        await self.session.flush()
        return attempt

    async def finish(
        self,
        attempt_id: str,
        status: AttemptStatus,
        failure_class: str | None = None,
        output: dict | None = None,
    ) -> None:
        row = await self.session.get(TaskAttemptModel, attempt_id)
        if row is not None:
            row.status = status.value
            row.failure_class = failure_class
            row.output_json = json.dumps(output) if output is not None else None
            row.finished_at = _now()
            await self.session.flush()


# CRUD for human-approval requests
class ApprovalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, proposal: ApprovalProposal) -> None:
        self.session.add(
            ApprovalModel(
                id=proposal.proposal_id,
                execution_id=proposal.execution_id,
                task_id=proposal.task_id,
                proposal_json=proposal.model_dump_json(),
                status=proposal.status.value,
                created_at=proposal.created_at,
                decided_at=None,
                expires_at=proposal.expires_at,
            )
        )
        await self.session.flush()

    async def get(self, proposal_id: str) -> ApprovalProposal | None:
        row = await self.session.get(ApprovalModel, proposal_id)
        return ApprovalProposal.model_validate_json(row.proposal_json) if row is not None else None

    async def get_latest_for_task(self, execution_id: str, task_id: str) -> ApprovalProposal | None:
        # Same fixed plan repeats task_ids across executions (e.g.
        # "create_event"), so this must be scoped by execution_id too.
        result = await self.session.execute(
            select(ApprovalModel)
            .where(ApprovalModel.execution_id == execution_id, ApprovalModel.task_id == task_id)
            .order_by(ApprovalModel.created_at.desc())
        )
        row = result.scalars().first()
        return ApprovalProposal.model_validate_json(row.proposal_json) if row is not None else None

    async def update_status(self, proposal_id: str, status: ApprovalStatus) -> None:
        row = await self.session.get(ApprovalModel, proposal_id)
        if row is not None:
            proposal = ApprovalProposal.model_validate_json(row.proposal_json)
            proposal = proposal.model_copy(update={"status": status, "decided_at": _now()})
            row.proposal_json = proposal.model_dump_json()
            row.status = status.value
            row.decided_at = proposal.decided_at
            await self.session.flush()


# Appends events to an execution's audit timeline
class ExecutionEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: ExecutionEvent) -> None:
        self.session.add(
            ExecutionEventModel(
                id=event.event_id,
                execution_id=event.execution_id,
                event_type=event.event_type,
                task_id=event.task_id,
                agent_id=event.agent_id,
                attempt_id=event.attempt_id,
                payload_json=json.dumps(event.payload, default=str),
                occurred_at=event.occurred_at,
            )
        )
        await self.session.flush()

    async def list_by_execution(self, execution_id: str) -> list[ExecutionEvent]:
        result = await self.session.execute(
            select(ExecutionEventModel)
            .where(ExecutionEventModel.execution_id == execution_id)
            .order_by(ExecutionEventModel.occurred_at)
        )
        return [
            ExecutionEvent(
                event_id=row.id,
                execution_id=row.execution_id,
                event_type=row.event_type,
                task_id=row.task_id,
                agent_id=row.agent_id,
                attempt_id=row.attempt_id,
                payload=json.loads(row.payload_json),
                occurred_at=row.occurred_at,
            )
            for row in result.scalars().all()
        ]
