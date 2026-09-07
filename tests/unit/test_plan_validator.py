"""Unit tests for PlanValidator — pure, no DB, no LLM."""

import pytest
from demo.seed import build_agent_catalogue

from synapse_plane.domain.enums import RiskLevel
from synapse_plane.domain.workflow import TaskDefinition, WorkflowDefinition
from synapse_plane.planning.errors import UnsupportedCapabilityError
from synapse_plane.planning.fake_planner import (
    DINNER_WORKFLOW_PLAN,
    TRAVEL_WORKFLOW_PLAN,
    FakePlanner,
)
from synapse_plane.planning.plan_validator import PlanValidator

CATALOGUE = build_agent_catalogue()


def make_task(**overrides: object) -> TaskDefinition:
    defaults: dict[str, object] = {
        "task_id": "t1",
        "task_type": "agent_task",
        "description": "test task",
        "required_capability": "context.retrieve",
        "depends_on": [],
        "input_bindings": {},
        "output_schema": "Any@1",
        "risk_level": RiskLevel.READ_ONLY,
        "approval_required": False,
    }
    defaults.update(overrides)
    return TaskDefinition(**defaults)  # type: ignore[arg-type]


def test_valid_plan_passes() -> None:
    result = PlanValidator().validate(DINNER_WORKFLOW_PLAN, CATALOGUE)
    assert result.valid is True
    assert result.errors == []


def test_travel_plan_passes() -> None:
    result = PlanValidator().validate(TRAVEL_WORKFLOW_PLAN, CATALOGUE)
    assert result.valid is True
    assert result.errors == []


def test_duplicate_task_ids_rejected() -> None:
    plan = WorkflowDefinition(
        workflow_id="wf",
        goal="test",
        tasks=[make_task(task_id="t1"), make_task(task_id="t1")],
    )
    result = PlanValidator().validate(plan, CATALOGUE)
    assert result.valid is False
    assert any("Duplicate task IDs" in e for e in result.errors)


def test_unknown_capability_rejected() -> None:
    plan = WorkflowDefinition(
        workflow_id="wf", goal="test", tasks=[make_task(required_capability="made.up.capability")]
    )
    result = PlanValidator().validate(plan, CATALOGUE)
    assert result.valid is False
    assert any("unknown capability" in e for e in result.errors)


def test_prohibited_capability_rejected() -> None:
    plan = WorkflowDefinition(
        workflow_id="wf", goal="test", tasks=[make_task(required_capability="flight.book")]
    )
    result = PlanValidator().validate(plan, CATALOGUE)
    assert result.valid is False
    assert any("prohibited capability" in e for e in result.errors)


def test_cyclic_dependency_rejected() -> None:
    plan = WorkflowDefinition(
        workflow_id="wf",
        goal="test",
        tasks=[
            make_task(task_id="a", depends_on=["b"]),
            make_task(task_id="b", depends_on=["a"]),
        ],
    )
    result = PlanValidator().validate(plan, CATALOGUE)
    assert result.valid is False
    assert any("Cyclic dependency" in e for e in result.errors)


def test_missing_dependency_reference_rejected() -> None:
    plan = WorkflowDefinition(
        workflow_id="wf", goal="test", tasks=[make_task(task_id="a", depends_on=["ghost"])]
    )
    result = PlanValidator().validate(plan, CATALOGUE)
    assert result.valid is False
    assert any("depends on unknown task" in e for e in result.errors)


def test_binding_referencing_nonexistent_task_rejected() -> None:
    plan = WorkflowDefinition(
        workflow_id="wf",
        goal="test",
        tasks=[make_task(task_id="a", input_bindings={"x": "$tasks.ghost.output"})],
    )
    result = PlanValidator().validate(plan, CATALOGUE)
    assert result.valid is False
    assert any("references unknown task" in e for e in result.errors)


async def test_fake_planner_returns_dinner_plan_for_dinner_intent() -> None:
    plan = await FakePlanner().plan(
        "Arrange dinner with Maya tomorrow", None, CATALOGUE
    )  # type: ignore[arg-type]
    assert plan.workflow_id == DINNER_WORKFLOW_PLAN.workflow_id


async def test_fake_planner_returns_travel_plan_for_travel_intent() -> None:
    plan = await FakePlanner().plan(
        "Compare a trip to Kandy and Galle", None, CATALOGUE
    )  # type: ignore[arg-type]
    assert plan.workflow_id == TRAVEL_WORKFLOW_PLAN.workflow_id


async def test_fake_planner_rejects_unsupported_intent() -> None:
    with pytest.raises(UnsupportedCapabilityError):
        await FakePlanner().plan(  # type: ignore[arg-type]
            "Book me the cheapest flight to Singapore", None, CATALOGUE
        )
