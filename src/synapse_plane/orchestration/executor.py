"""Dispatches one task to a selected agent, with retry, fallback, and the
approval gate. The gate is checked BEFORE the agent runs for a
CONSEQUENTIAL_WRITE task, since running the agent IS the external effect.

db_lock serializes access to the shared AsyncSession: SQLAlchemy's AsyncSession
is not safe for concurrent use from multiple coroutines, but agent_instance.execute()
itself runs unlocked so genuinely concurrent tasks (per FR-008) still overlap in
wall-clock time — only the bookkeeping around them is serialized.
"""

import asyncio
from typing import Any

from synapse_plane.agents.base import AgentInput, BaseAgent
from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import ApprovalStatus, AttemptStatus, TaskStatus
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.workflow import TaskDefinition
from synapse_plane.observability.event_emitter import EventEmitter
from synapse_plane.orchestration.binding_resolver import BindingResolver
from synapse_plane.orchestration.errors import ApprovalRequiredError
from synapse_plane.persistence.execution_repositories import (
    ApprovalRepository,
    TaskAttemptRepository,
    TaskRepository,
)
from synapse_plane.policies.approval_policy import ApprovalPolicy
from synapse_plane.policies.retry_policy import RetryPolicy
from synapse_plane.registry.capability_router import CapabilityRouter
from synapse_plane.registry.errors import NoEligibleAgentError


# Runs one task to completion: select agent, resolve inputs, execute, retry/fallback/gate
class AgentExecutor:
    def __init__(
        self,
        router: CapabilityRouter,
        agent_registry: dict[str, BaseAgent],
        binding_resolver: BindingResolver,
        retry_policy: RetryPolicy,
        approval_policy: ApprovalPolicy,
        task_repo: TaskRepository,
        attempt_repo: TaskAttemptRepository,
        approval_repo: ApprovalRepository,
        emitter: EventEmitter,
        db_lock: asyncio.Lock,
    ):
        self.router = router
        self.agent_registry = agent_registry
        self.binding_resolver = binding_resolver
        self.retry_policy = retry_policy
        self.approval_policy = approval_policy
        self.task_repo = task_repo
        self.attempt_repo = attempt_repo
        self.approval_repo = approval_repo
        self.emitter = emitter
        self.db_lock = db_lock

    async def run_task(
        self,
        task: TaskDefinition,
        execution_id: str,
        task_outputs: dict[str, dict[str, Any]],
        catalogue: list[AgentManifest],
        profile: UserProfile,
        base_context: dict[str, Any],
    ) -> dict[str, Any]:
        resolved_inputs = self.binding_resolver.resolve(task.input_bindings, task_outputs)

        if self.approval_policy.requires_approval(task):
            async with self.db_lock:
                await self._enforce_approval_gate(task, execution_id, resolved_inputs, profile)

        excluded_agents: list[str] = []
        router_result = self.router.select(
            task.required_capability, catalogue, exclude_ids=excluded_agents
        )
        selected = router_result.selected
        async with self.db_lock:
            await self.emitter.emit(
                execution_id,
                "agent.selected",
                task_id=task.task_id,
                agent_id=selected.agent_id,
                reason=router_result.selection_reason,
            )

        agent_input = AgentInput(
            goal=task.description,
            task_id=task.task_id,
            execution_id=execution_id,
            context={**base_context, **resolved_inputs},
            required_capability=task.required_capability,
            timeout_seconds=task.timeout_seconds,
        )

        attempt_number = 0
        while True:
            attempt_number += 1
            async with self.db_lock:
                attempt = await self.attempt_repo.create(
                    f"{execution_id}:{task.task_id}", attempt_number, selected.agent_id
                )
                await self.emitter.emit(
                    execution_id,
                    "task.started",
                    task_id=task.task_id,
                    agent_id=selected.agent_id,
                    attempt_id=attempt.attempt_id,
                )

            try:
                agent_instance = self.agent_registry[selected.agent_id]
                output = await agent_instance.execute(agent_input)  # not locked — the real work
                async with self.db_lock:
                    await self.attempt_repo.finish(
                        attempt.attempt_id, AttemptStatus.SUCCEEDED, output=output.result
                    )
                    await self.task_repo.update_output(
                        execution_id, task.task_id, output.result, selected.agent_id
                    )
                    # An agent can recover from its own tool failure internally
                    # (e.g. a search tool timing out, falling back to a backup
                    # tool) without ever raising — the executor never sees a
                    # failure to retry or route around. That's real resilience,
                    # but invisible in the timeline unless called out here.
                    fallback_tool = next(
                        (t for t in output.tool_calls_made if "fallback" in t.lower()), None
                    )
                    if fallback_tool:
                        await self.emitter.emit(
                            execution_id,
                            "tool.fallback_used",
                            task_id=task.task_id,
                            agent_id=selected.agent_id,
                            tool=fallback_tool,
                        )
                    await self.emitter.emit(
                        execution_id,
                        "task.succeeded",
                        task_id=task.task_id,
                        agent_id=selected.agent_id,
                    )
                return output.result

            except Exception as error:  # noqa: BLE001 — classified immediately below
                failure_class = self.retry_policy.classify_failure(error)
                async with self.db_lock:
                    await self.attempt_repo.finish(
                        attempt.attempt_id, AttemptStatus.FAILED, failure_class=failure_class.value
                    )
                    await self.emitter.emit(
                        execution_id,
                        "task.failed",
                        task_id=task.task_id,
                        agent_id=selected.agent_id,
                        error=str(error),
                        failure_class=failure_class.value,
                    )

                if self.retry_policy.should_retry(failure_class, attempt_number):
                    await asyncio.sleep(self.retry_policy.backoff_seconds(attempt_number))
                    async with self.db_lock:
                        await self.emitter.emit(
                            execution_id, "task.retry_scheduled", task_id=task.task_id
                        )
                    continue

                if self.retry_policy.should_fallback(failure_class):
                    excluded_agents.append(selected.agent_id)
                    try:
                        router_result = self.router.select(
                            task.required_capability, catalogue, exclude_ids=excluded_agents
                        )
                    except NoEligibleAgentError as no_fallback:
                        # no fallback available — surface the original failure
                        raise error from no_fallback
                    selected = router_result.selected
                    async with self.db_lock:
                        await self.emitter.emit(
                            execution_id,
                            "agent.fallback_selected",
                            task_id=task.task_id,
                            agent_id=selected.agent_id,
                        )
                    attempt_number = 0
                    continue

                raise

    async def _enforce_approval_gate(
        self,
        task: TaskDefinition,
        execution_id: str,
        resolved_inputs: dict[str, Any],
        profile: UserProfile,
    ) -> None:
        """Caller (run_task) already holds db_lock."""
        existing = await self.approval_repo.get_latest_for_task(execution_id, task.task_id)

        if existing is None:
            proposal = self.approval_policy.build_proposal(
                execution_id=execution_id,
                task_id=task.task_id,
                recommendation=resolved_inputs.get("recommendation", {}),
                time_slot=resolved_inputs.get("availability", {}),
                profile=profile,
            )
            await self.approval_repo.create(proposal)
            await self.task_repo.update_status(
                execution_id, task.task_id, TaskStatus.WAITING_FOR_APPROVAL
            )
            await self.emitter.emit(execution_id, "approval.requested", task_id=task.task_id)
            raise ApprovalRequiredError(proposal.proposal_id)

        if existing.status != ApprovalStatus.APPROVED:
            raise ApprovalRequiredError(existing.proposal_id)
