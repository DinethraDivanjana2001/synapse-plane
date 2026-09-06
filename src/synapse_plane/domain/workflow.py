"""Typed task graph produced by the planning agent and enforced by the
deterministic PlanValidator. See docs/REQUIREMENTS.md FR-003/FR-004.
"""

from typing import Any

from pydantic import BaseModel, Field

from synapse_plane.domain.enums import RiskLevel


class TaskDefinition(BaseModel):
    task_id: str
    task_type: str
    description: str
    required_capability: str
    depends_on: list[str] = Field(default_factory=list)
    input_bindings: dict[str, str] = Field(default_factory=dict)
    output_schema: str
    risk_level: RiskLevel
    approval_required: bool
    retry_policy: str = "transient-default"
    timeout_seconds: int = 30


class WorkflowDefinition(BaseModel):
    workflow_id: str
    goal: str
    planning_version: int = 1
    max_replan_count: int = 2
    tasks: list[TaskDefinition] = Field(default_factory=list)
    global_constraints: dict[str, Any] = Field(default_factory=dict)
