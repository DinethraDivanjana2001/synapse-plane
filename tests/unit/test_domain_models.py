"""Unit tests for Pydantic domain models — no DB, no LLM, no external I/O."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import (
    AgentHealthStatus,
    AgentImplementationStatus,
    AgentOwnership,
    AgentTrustStatus,
    ExplicitOrInferred,
    MemoryType,
    SideEffectLevel,
)
from synapse_plane.domain.execution import ApprovalProposal
from synapse_plane.domain.memory import ContextPackage, Memory
from synapse_plane.domain.profile import (
    ApprovalPolicyConfig,
    CalendarConfig,
    FoodPreferences,
    Location,
    TravelPreferences,
    UserProfile,
)
from synapse_plane.domain.workflow import WorkflowDefinition


def _now() -> datetime:
    return datetime.now(UTC)


def make_profile() -> UserProfile:
    return UserProfile(
        user_id="user-dinethra",
        display_name="Dinethra",
        home_location=Location(label="Colombo", latitude=6.9271, longitude=79.8612),
        timezone="Asia/Colombo",
        food_preferences=FoodPreferences(cuisines=["italian"]),
        travel_preferences=TravelPreferences(interests=["hiking"]),
        calendar=CalendarConfig(),
        approval_policy=ApprovalPolicyConfig(),
    )


def make_memory(**overrides: object) -> Memory:
    defaults: dict[str, object] = {
        "memory_id": "mem-1",
        "user_id": "user-dinethra",
        "memory_type": MemoryType.PREFERENCE,
        "content": "I prefer quiet restaurants",
        "confidence": 0.95,
        "explicit_or_inferred": ExplicitOrInferred.EXPLICIT,
        "valid_from": _now(),
        "source": "user_input",
        "created_at": _now(),
        "observed_at": _now(),
    }
    defaults.update(overrides)
    return Memory(**defaults)  # type: ignore[arg-type]


def test_valid_user_profile_deserializes() -> None:
    profile = make_profile()
    assert profile.user_id == "user-dinethra"
    assert profile.home_location.label == "Colombo"


def test_invalid_risk_level_raises() -> None:
    with pytest.raises(ValidationError):
        WorkflowDefinition.model_validate(
            {
                "workflow_id": "wf-1",
                "goal": "test",
                "tasks": [
                    {
                        "task_id": "t1",
                        "task_type": "noop",
                        "description": "d",
                        "required_capability": "profile.read",
                        "output_schema": "Any",
                        "risk_level": "NOT_A_REAL_LEVEL",
                        "approval_required": False,
                    }
                ],
            }
        )


def test_memory_with_no_valid_to_is_currently_valid() -> None:
    memory = make_memory(valid_to=None)
    assert memory.is_currently_valid is True


def test_memory_with_valid_to_is_not_currently_valid() -> None:
    memory = make_memory(valid_to=_now())
    assert memory.is_currently_valid is False


def test_context_package_has_provenance() -> None:
    from synapse_plane.domain.memory import ContextItem

    memory = make_memory()
    package = ContextPackage(
        items=[
            ContextItem(memory=memory, relevance_score=0.8, retrieval_reason="semantic_similarity")
        ],
        intent="find a quiet restaurant",
        retrieved_at=_now(),
        total_memories_scanned=30,
        token_estimate=42,
    )
    assert package.provenance == ["preference:user_input"]


def test_workflow_definition_with_zero_tasks_is_valid() -> None:
    workflow = WorkflowDefinition(workflow_id="wf-empty", goal="noop")
    assert workflow.tasks == []


def test_agent_manifest_with_missing_required_fields_raises() -> None:
    with pytest.raises(ValidationError):
        AgentManifest.model_validate({"agent_id": "a1"})


def test_agent_manifest_is_eligible_only_when_approved_and_enabled() -> None:
    manifest = AgentManifest(
        agent_id="internal-context-intelligence",
        name="Context Intelligence",
        ownership=AgentOwnership.INTERNAL,
        version="1.0.0",
        description="Hybrid RAG retrieval agent",
        capabilities=["context.retrieve"],
        side_effect_level=SideEffectLevel.READ_ONLY,
        trust_status=AgentTrustStatus.APPROVED,
        enabled=True,
        health_status=AgentHealthStatus.HEALTHY,
        implementation_status=AgentImplementationStatus.FULLY_IMPLEMENTED,
    )
    assert manifest.is_eligible is True

    disabled = manifest.model_copy(update={"enabled": False})
    assert disabled.is_eligible is False

    revoked = manifest.model_copy(update={"trust_status": AgentTrustStatus.REVOKED})
    assert revoked.is_eligible is False


def test_approval_proposal_action_digest_is_a_string() -> None:
    proposal = ApprovalProposal(
        proposal_id="prop-1",
        execution_id="exec-1",
        task_id="task-create-event",
        restaurant_name="La Foresta",
        address="Colombo 03",
        start_time=_now(),
        end_time=_now(),
        timezone="Asia/Colombo",
        calendar_id="primary",
        description="Dinner with Maya",
        tool_identifier="calendar_write_tool",
        action_digest="a" * 64,
        created_at=_now(),
        expires_at=_now(),
    )
    assert isinstance(proposal.action_digest, str)
