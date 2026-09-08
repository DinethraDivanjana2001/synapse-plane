"""Dependency-aware scheduler: runs ready tasks concurrently, reconstructs
ready-state purely from the DB (no in-memory call stack required to resume).

db_lock serializes access to the shared AsyncSession (see executor.py) —
never held across an executor.run_task() call, since the executor acquires
the same lock internally and asyncio.Lock is not reentrant.
"""

import asyncio

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import ExecutionStatus, TaskStatus
from synapse_plane.domain.execution import Task
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.workflow import TaskDefinition, WorkflowDefinition
from synapse_plane.observability.event_emitter import EventEmitter
from synapse_plane.orchestration.errors import ApprovalRequiredError
from synapse_plane.orchestration.executor import AgentExecutor
from synapse_plane.persistence.execution_repositories import ExecutionRepository, TaskRepository

_TERMINAL_STATUSES = {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED, TaskStatus.SKIPPED}


# Drives one execution to completion, pausing cleanly at approval gates
class DependencyScheduler:
    def __init__(
        self,
        execution_repo: ExecutionRepository,
        task_repo: TaskRepository,
        executor: AgentExecutor,
        emitter: EventEmitter,
        catalogue: list[AgentManifest],
        profile: UserProfile,
        base_context: dict[str, object],
        db_lock: asyncio.Lock,
    ):
        self.execution_repo = execution_repo
        self.task_repo = task_repo
        self.executor = executor
        self.emitter = emitter
        self.catalogue = catalogue
        self.profile = profile
        self.base_context = base_context
        self.db_lock = db_lock

    async def run(self, execution_id: str, workflow: WorkflowDefinition) -> None:
        async with self.db_lock:
            await self.execution_repo.update_status(execution_id, ExecutionStatus.RUNNING)
            task_outputs = {
                t.task_id: t.output
                for t in await self.task_repo.get_by_execution(execution_id)
                if t.status == TaskStatus.SUCCEEDED and t.output is not None
            }

        while True:
            async with self.db_lock:
                all_tasks = await self.task_repo.get_by_execution(execution_id)
                ready = self._get_ready_tasks(all_tasks, workflow, task_outputs)

                if not ready:
                    if all(t.status in _TERMINAL_STATUSES for t in all_tasks):
                        await self.execution_repo.update_status(
                            execution_id, ExecutionStatus.COMPLETED
                        )
                        await self.emitter.emit(execution_id, "execution.completed")
                        return
                    if any(t.status == TaskStatus.WAITING_FOR_APPROVAL for t in all_tasks):
                        await self.execution_repo.update_status(
                            execution_id, ExecutionStatus.WAITING_FOR_APPROVAL
                        )
                        return
                    await self.execution_repo.update_status(execution_id, ExecutionStatus.FAILED)
                    await self.emitter.emit(execution_id, "execution.failed")
                    return

                for task in ready:
                    await self.task_repo.update_status(task.task_id, TaskStatus.RUNNING)

            await asyncio.gather(
                *[self._run_single(t, workflow, execution_id, task_outputs) for t in ready]
            )

    async def resume_after_approval(self, execution_id: str, workflow: WorkflowDefinition) -> None:
        async with self.db_lock:
            await self.execution_repo.update_status(execution_id, ExecutionStatus.RESUMING)
            await self.emitter.emit(execution_id, "execution.resumed")
            for task in await self.task_repo.get_by_execution(execution_id):
                if task.status == TaskStatus.WAITING_FOR_APPROVAL:
                    await self.task_repo.update_status(task.task_id, TaskStatus.PENDING)
        await self.run(execution_id, workflow)

    def _get_ready_tasks(
        self, all_tasks: list[Task], workflow: WorkflowDefinition, task_outputs: dict[str, dict]
    ) -> list[Task]:
        succeeded_ids = set(task_outputs.keys())
        ready = []
        for task in all_tasks:
            if task.status != TaskStatus.PENDING:
                continue
            task_def = self._definition_for(workflow, task.task_id)
            if all(dep in succeeded_ids for dep in task_def.depends_on):
                ready.append(task)
        return ready

    async def _run_single(
        self,
        task: Task,
        workflow: WorkflowDefinition,
        execution_id: str,
        task_outputs: dict[str, dict],
    ) -> None:
        task_def = self._definition_for(workflow, task.task_id)

        try:
            output = await self.executor.run_task(
                task_def,
                execution_id,
                task_outputs,
                self.catalogue,
                self.profile,
                self.base_context,
            )
            task_outputs[task.task_id] = output
            async with self.db_lock:
                await self.task_repo.update_status(task.task_id, TaskStatus.SUCCEEDED)
        except ApprovalRequiredError:
            pass  # executor already moved the task to WAITING_FOR_APPROVAL
        except Exception:  # noqa: BLE001 — terminal failure for this task, block downstream
            async with self.db_lock:
                await self.task_repo.update_status(task.task_id, TaskStatus.FAILED)
                await self._block_downstream(task.task_id, workflow, execution_id)

    async def _block_downstream(
        self, failed_task_id: str, workflow: WorkflowDefinition, execution_id: str
    ) -> None:
        """Caller already holds db_lock."""
        for task in await self.task_repo.get_by_execution(execution_id):
            task_def = self._definition_for(workflow, task.task_id)
            if failed_task_id in task_def.depends_on and task.status == TaskStatus.PENDING:
                await self.task_repo.update_status(task.task_id, TaskStatus.BLOCKED)

    @staticmethod
    def _definition_for(workflow: WorkflowDefinition, task_id: str) -> TaskDefinition:
        return next(t for t in workflow.tasks if t.task_id == task_id)
