"""Execution, task, attempt, event, and approval domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from synapse_plane.domain.enums import (
    ApprovalStatus,
    AttemptStatus,
    ExecutionStatus,
    FailureClass,
    TaskStatus,
)
from synapse_plane.domain.workflow import TaskDefinition, WorkflowDefinition


# One user intent being executed, with its overall status
class Execution(BaseModel):
    execution_id: str
    user_id: str
    intent_text: str
    status: ExecutionStatus
    created_at: datetime
    updated_at: datetime


# One planned/re-planned task DAG version for an execution
class WorkflowVersionRecord(BaseModel):
    workflow_version_id: str
    execution_id: str
    planning_version: int
    workflow: WorkflowDefinition
    created_at: datetime


# One task within a workflow version, and its current state
class Task(BaseModel):
    task_id: str
    execution_id: str
    workflow_version_id: str
    definition: TaskDefinition
    status: TaskStatus
    selected_agent_id: str | None = None
    output: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# One execution attempt of a task by a specific agent
class TaskAttempt(BaseModel):
    attempt_id: str
    task_id: str
    attempt_number: int
    agent_id: str
    status: AttemptStatus
    failure_class: FailureClass | None = None
    output: dict[str, Any] | None = None
    started_at: datetime
    finished_at: datetime | None = None


# One entry in an execution's timeline
class ExecutionEvent(BaseModel):
    event_id: str
    execution_id: str
    event_type: str
    task_id: str | None = None
    agent_id: str | None = None
    attempt_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime


# Consequential-action proposal awaiting human approval
class ApprovalProposal(BaseModel):
    proposal_id: str
    execution_id: str
    task_id: str
    context_package_id: str | None = None
    restaurant_name: str
    address: str
    start_time: datetime
    end_time: datetime
    timezone: str
    calendar_id: str
    description: str
    tool_identifier: str
    action_digest: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime
    decided_at: datetime | None = None
    expires_at: datetime
