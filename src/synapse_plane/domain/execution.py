"""Execution event history and approval proposal domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from synapse_plane.domain.enums import ApprovalStatus


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
    expires_at: datetime
