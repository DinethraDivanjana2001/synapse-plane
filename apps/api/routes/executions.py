"""Execution endpoints: create, inspect, approve/reject.

create_execution runs synchronously to the first pause point (WAITING_FOR_
APPROVAL / COMPLETED / FAILED) rather than firing a detached background
task — simpler and deterministic for a prototype's demo scenarios. A
production system would return immediately and stream progress instead.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from synapse_plane.config import Settings, get_settings
from synapse_plane.domain.enums import ApprovalStatus, ExecutionStatus, TaskStatus
from synapse_plane.observability.event_emitter import EventEmitter
from synapse_plane.orchestration.wiring import DEMO_USER_ID, build_scheduler, get_planner
from synapse_plane.persistence.execution_repositories import (
    ApprovalRepository,
    ExecutionEventRepository,
    ExecutionRepository,
    TaskRepository,
    WorkflowVersionRepository,
)
from synapse_plane.persistence.repositories import AgentManifestRepository, UserProfileRepository
from synapse_plane.planning.errors import UnsupportedCapabilityError
from synapse_plane.planning.plan_validator import PlanValidator

router = APIRouter(prefix="/executions", tags=["executions"])


class CreateExecutionRequest(BaseModel):
    intent: str
    inject_failure: bool = False
    preferred_time: str | None = None  # "19:00" — overrides the profile default


class ApprovalDecisionRequest(BaseModel):
    """Optional overrides applied before the approved action runs — this is
    how the user picks a different restaurant or time slot than the one the
    system proposed."""

    selected_restaurant: dict | None = None
    selected_start_time: str | None = None
    selected_end_time: str | None = None


class TaskSummary(BaseModel):
    task_id: str
    status: str
    selected_agent_id: str | None
    output: dict | None


class ExecutionDetail(BaseModel):
    execution_id: str
    status: str
    intent_text: str
    tasks: list[TaskSummary]
    pending_approval: dict | None = None
    error: dict | None = None


class EventSummary(BaseModel):
    event_type: str
    task_id: str | None
    agent_id: str | None
    payload: dict
    occurred_at: str


async def _load_detail(
    execution_id: str,
    execution_repo: ExecutionRepository,
    task_repo: TaskRepository,
    approval_repo: ApprovalRepository,
) -> ExecutionDetail:
    execution = await execution_repo.get(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    tasks = await task_repo.get_by_execution(execution_id)

    pending_approval = None
    if execution.status == ExecutionStatus.WAITING_FOR_APPROVAL:
        waiting_task = next((t for t in tasks if t.status == TaskStatus.WAITING_FOR_APPROVAL), None)
        if waiting_task is not None:
            proposal = await approval_repo.get_latest_for_task(execution_id, waiting_task.task_id)
            if proposal is not None:
                pending_approval = proposal.model_dump(mode="json")

    return ExecutionDetail(
        execution_id=execution.execution_id,
        status=execution.status.value,
        intent_text=execution.intent_text,
        tasks=[
            TaskSummary(
                task_id=t.task_id,
                status=t.status.value,
                selected_agent_id=t.selected_agent_id,
                output=t.output,
            )
            for t in tasks
        ],
        pending_approval=pending_approval,
    )


async def _fetch_relevant_facts(db: AsyncSession, settings: Settings, intent: str) -> list[str]:
    """The same retrieval the context.retrieve task runs later, called once
    up front so the planner can write a person-aware "requirements" string
    (e.g. Rebecca's known fast-food preference, not the user's own profile
    default) instead of only ever seeing the aggregate profile."""
    from synapse_plane.orchestration.wiring import DEMO_USER_ID, get_embedding_service
    from synapse_plane.persistence.repositories import EntityRepository, MemoryRepository
    from synapse_plane.retrieval.context_retriever import HybridContextRetriever

    retriever = HybridContextRetriever(
        memory_repo=MemoryRepository(db),
        entity_repo=EntityRepository(db),
        embedding_service=get_embedding_service(settings),
        settings=settings,
    )
    package = await retriever.retrieve(intent, DEMO_USER_ID)
    return [item.memory.content for item in package.items[:8]]


@router.post("", response_model=ExecutionDetail, status_code=201)
async def create_execution(
    body: CreateExecutionRequest, db: AsyncSession = Depends(get_db)
) -> ExecutionDetail:
    settings = get_settings()
    execution_repo = ExecutionRepository(db)
    task_repo = TaskRepository(db)
    approval_repo = ApprovalRepository(db)
    workflow_version_repo = WorkflowVersionRepository(db)
    profile_repo = UserProfileRepository(db)
    agent_repo = AgentManifestRepository(db)
    emitter = EventEmitter(ExecutionEventRepository(db))

    execution = await execution_repo.create(DEMO_USER_ID, body.intent)
    await emitter.emit(execution.execution_id, "execution.created")

    profile = await profile_repo.get(DEMO_USER_ID)
    if profile is None:
        raise HTTPException(status_code=500, detail="Demo profile not seeded")
    catalogue = await agent_repo.list_all()

    planner = get_planner(settings)
    relevant_facts = await _fetch_relevant_facts(db, settings, body.intent)
    await emitter.emit(execution.execution_id, "planning.started")
    try:
        plan = await planner.plan(body.intent, profile, catalogue, relevant_facts)
    except UnsupportedCapabilityError as exc:
        await execution_repo.update_status(execution.execution_id, ExecutionStatus.FAILED)
        await emitter.emit(
            execution.execution_id,
            "plan.rejected",
            error_code="UNSUPPORTED_CAPABILITY",
            capabilities=exc.capabilities,
        )
        await db.commit()
        detail = await _load_detail(
            execution.execution_id, execution_repo, task_repo, approval_repo
        )
        detail.error = {"error_code": "UNSUPPORTED_CAPABILITY", "capabilities": exc.capabilities}
        return detail
    except Exception as exc:  # noqa: BLE001 — LLM output boundary: never a plan, always FAILED
        await execution_repo.update_status(execution.execution_id, ExecutionStatus.FAILED)
        await emitter.emit(
            execution.execution_id, "plan.rejected", error_code="PLANNING_FAILED", detail=str(exc)
        )
        await db.commit()
        detail = await _load_detail(
            execution.execution_id, execution_repo, task_repo, approval_repo
        )
        detail.error = {"error_code": "PLANNING_FAILED", "errors": [str(exc)]}
        return detail

    await emitter.emit(execution.execution_id, "plan.proposed")
    validation = PlanValidator().validate(plan, catalogue)
    if not validation.valid:
        await execution_repo.update_status(execution.execution_id, ExecutionStatus.FAILED)
        await emitter.emit(
            execution.execution_id,
            "plan.rejected",
            error_code="INVALID_PLAN",
            errors=validation.errors,
        )
        await db.commit()
        detail = await _load_detail(
            execution.execution_id, execution_repo, task_repo, approval_repo
        )
        detail.error = {"error_code": "INVALID_PLAN", "errors": validation.errors}
        return detail
    await emitter.emit(execution.execution_id, "plan.validated")

    # A plan with only a context.retrieve task is how the real-mode planner
    # signals "out of scope" (see prompt_builder's SCOPE rules) — reject it
    # immediately, the same way demo mode's UnsupportedCapabilityError does,
    # rather than running it to a misleadingly-green COMPLETED.
    if len(plan.tasks) == 1 and plan.tasks[0].required_capability == "context.retrieve":
        await execution_repo.update_status(execution.execution_id, ExecutionStatus.FAILED)
        await emitter.emit(
            execution.execution_id, "plan.rejected", error_code="UNSUPPORTED_CAPABILITY"
        )
        await db.commit()
        detail = await _load_detail(
            execution.execution_id, execution_repo, task_repo, approval_repo
        )
        detail.error = {
            "error_code": "UNSUPPORTED_CAPABILITY",
            "errors": [
                "This request is outside what SynapsePlane can do. It handles dining "
                "(finding restaurants, booking a table into your calendar) and travel "
                "destination comparison. Nothing was booked or changed."
            ],
        }
        return detail

    version = await workflow_version_repo.create(execution.execution_id, plan)
    await task_repo.create_from_workflow(execution.execution_id, version.workflow_version_id, plan)
    await db.commit()

    scheduler = build_scheduler(
        db,
        settings,
        catalogue,
        profile,
        inject_failure=body.inject_failure,
        preferred_time=body.preferred_time,
        intent=body.intent,
    )
    await scheduler.run(execution.execution_id, plan)
    await db.commit()

    return await _load_detail(execution.execution_id, execution_repo, task_repo, approval_repo)


@router.get("/{execution_id}", response_model=ExecutionDetail)
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)) -> ExecutionDetail:
    return await _load_detail(
        execution_id, ExecutionRepository(db), TaskRepository(db), ApprovalRepository(db)
    )


@router.get("/{execution_id}/events", response_model=list[EventSummary])
async def get_events(execution_id: str, db: AsyncSession = Depends(get_db)) -> list[EventSummary]:
    events = await ExecutionEventRepository(db).list_by_execution(execution_id)
    return [
        EventSummary(
            event_type=e.event_type,
            task_id=e.task_id,
            agent_id=e.agent_id,
            payload=e.payload,
            occurred_at=e.occurred_at.isoformat(),
        )
        for e in events
    ]


async def _apply_user_overrides(
    execution_id: str, task_repo: TaskRepository, body: ApprovalDecisionRequest
) -> None:
    """Rewrite the recommendation / availability task outputs to match what
    the user actually chose. Task ids are LLM-generated and vary per run, so
    tasks are matched by output shape rather than by name."""
    for task in await task_repo.get_by_execution(execution_id):
        output = task.output
        if not isinstance(output, dict):
            continue

        if body.selected_restaurant and "selected" in output:
            await task_repo.update_output(
                execution_id,
                task.task_id,
                {**output, "selected": body.selected_restaurant},
                task.selected_agent_id,
            )
        elif body.selected_start_time and "start_time" in output:
            await task_repo.update_output(
                execution_id,
                task.task_id,
                {
                    **output,
                    "start_time": body.selected_start_time,
                    "end_time": body.selected_end_time or output.get("end_time"),
                },
                task.selected_agent_id,
            )


@router.post("/{execution_id}/approvals/{approval_id}/approve", response_model=ExecutionDetail)
async def approve(
    execution_id: str,
    approval_id: str,
    body: ApprovalDecisionRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> ExecutionDetail:
    settings = get_settings()
    execution_repo = ExecutionRepository(db)
    task_repo = TaskRepository(db)
    approval_repo = ApprovalRepository(db)
    workflow_version_repo = WorkflowVersionRepository(db)
    profile_repo = UserProfileRepository(db)
    agent_repo = AgentManifestRepository(db)
    emitter = EventEmitter(ExecutionEventRepository(db))

    execution = await execution_repo.get(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status != ExecutionStatus.WAITING_FOR_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Execution is not waiting for approval (status={execution.status.value})",
        )

    proposal = await approval_repo.get(approval_id)
    if proposal is None or proposal.execution_id != execution_id:
        raise HTTPException(status_code=404, detail="Approval not found")
    if proposal.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409, detail=f"Approval is not pending (status={proposal.status.value})"
        )

    # The create-event task binds its inputs from upstream task outputs, not
    # from the proposal — so a user's different pick has to be written back
    # into those outputs before the workflow resumes, or it would be ignored.
    if body is not None and (body.selected_restaurant or body.selected_start_time):
        await _apply_user_overrides(execution_id, task_repo, body)

    await approval_repo.update_status(approval_id, ApprovalStatus.APPROVED)
    await emitter.emit(execution_id, "approval.approved", task_id=proposal.task_id)
    await db.commit()

    profile = await profile_repo.get(DEMO_USER_ID)
    catalogue = await agent_repo.list_all()
    version = await workflow_version_repo.get_latest_for_execution(execution_id)
    if version is None or profile is None:
        raise HTTPException(status_code=500, detail="No workflow version or profile found")

    scheduler = build_scheduler(db, settings, catalogue, profile)
    await scheduler.resume_after_approval(execution_id, version.workflow)
    await db.commit()

    return await _load_detail(execution_id, execution_repo, task_repo, approval_repo)


@router.post("/{execution_id}/approvals/{approval_id}/reject", response_model=ExecutionDetail)
async def reject(
    execution_id: str, approval_id: str, db: AsyncSession = Depends(get_db)
) -> ExecutionDetail:
    execution_repo = ExecutionRepository(db)
    task_repo = TaskRepository(db)
    approval_repo = ApprovalRepository(db)
    emitter = EventEmitter(ExecutionEventRepository(db))

    execution = await execution_repo.get(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    proposal = await approval_repo.get(approval_id)
    if proposal is None or proposal.execution_id != execution_id:
        raise HTTPException(status_code=404, detail="Approval not found")

    await approval_repo.update_status(approval_id, ApprovalStatus.REJECTED)
    await task_repo.update_status(execution_id, proposal.task_id, TaskStatus.CANCELLED)
    await execution_repo.update_status(execution_id, ExecutionStatus.REJECTED)
    await emitter.emit(execution_id, "approval.rejected", task_id=proposal.task_id)
    await db.commit()

    return await _load_detail(execution_id, execution_repo, task_repo, approval_repo)
