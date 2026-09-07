"""Unit tests for CapabilityRouter — pure, no DB, no LLM."""

import pytest

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import (
    AgentHealthStatus,
    AgentImplementationStatus,
    AgentOwnership,
    AgentTrustStatus,
    SideEffectLevel,
)
from synapse_plane.registry.capability_router import CapabilityRouter
from synapse_plane.registry.errors import NoEligibleAgentError


def make_agent(**overrides: object) -> AgentManifest:
    defaults: dict[str, object] = {
        "agent_id": "agent-1",
        "name": "Agent One",
        "ownership": AgentOwnership.INTERNAL,
        "version": "1.0.0",
        "description": "test agent",
        "capabilities": ["context.retrieve"],
        "side_effect_level": SideEffectLevel.READ_ONLY,
        "trust_status": AgentTrustStatus.APPROVED,
        "enabled": True,
        "health_status": AgentHealthStatus.HEALTHY,
        "implementation_status": AgentImplementationStatus.FULLY_IMPLEMENTED,
        "reliability_score": 0.9,
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)  # type: ignore[arg-type]


def test_selects_highest_scored_eligible_agent() -> None:
    weak = make_agent(agent_id="weak", reliability_score=0.5)
    strong = make_agent(agent_id="strong", reliability_score=0.99)

    result = CapabilityRouter().select("context.retrieve", [weak, strong])

    assert result.selected.agent_id == "strong"
    assert len(result.candidates_evaluated) == 2


def test_excludes_disabled_agents() -> None:
    disabled = make_agent(agent_id="disabled", enabled=False)

    with pytest.raises(NoEligibleAgentError):
        CapabilityRouter().select("context.retrieve", [disabled])


def test_excludes_pending_review_agents() -> None:
    pending = make_agent(agent_id="pending", trust_status=AgentTrustStatus.PENDING_REVIEW)

    with pytest.raises(NoEligibleAgentError):
        CapabilityRouter().select("context.retrieve", [pending])


def test_excludes_unimplemented_agents() -> None:
    planned = make_agent(
        agent_id="planned", implementation_status=AgentImplementationStatus.PLANNED
    )

    with pytest.raises(NoEligibleAgentError):
        CapabilityRouter().select("context.retrieve", [planned])


def test_excludes_unavailable_health() -> None:
    down = make_agent(agent_id="down", health_status=AgentHealthStatus.UNAVAILABLE)

    with pytest.raises(NoEligibleAgentError):
        CapabilityRouter().select("context.retrieve", [down])


def test_raises_when_no_eligible_agent() -> None:
    other_capability = make_agent(capabilities=["web.discover_places"])

    with pytest.raises(NoEligibleAgentError):
        CapabilityRouter().select("context.retrieve", [other_capability])


def test_exclude_ids_removes_previously_failed_agent() -> None:
    only_agent = make_agent(agent_id="only")

    with pytest.raises(NoEligibleAgentError):
        CapabilityRouter().select("context.retrieve", [only_agent], exclude_ids=["only"])
