"""Deterministic agent selection — filter eligible agents, then score them."""

from dataclasses import dataclass, field

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.enums import AgentHealthStatus, AgentImplementationStatus
from synapse_plane.registry.errors import NoEligibleAgentError

_WORKING_IMPLEMENTATION_STATUSES = {
    AgentImplementationStatus.FULLY_IMPLEMENTED,
    AgentImplementationStatus.LIVE_EXTERNAL,
    AgentImplementationStatus.CONFIGURED,
}

_HEALTH_SCORE = {
    AgentHealthStatus.HEALTHY: 1.0,
    AgentHealthStatus.DEGRADED: 0.5,
    AgentHealthStatus.UNAVAILABLE: 0.0,
}
_MAX_LATENCY_MS = 60_000
_MAX_COST_UNITS = 10.0

# FR-006 weights — capability_fit is always 1.0 here since candidates are
# already filtered to only those offering the required capability
_WEIGHT_CAPABILITY_FIT = 0.35
_WEIGHT_RELIABILITY = 0.25
_WEIGHT_HEALTH = 0.15
_WEIGHT_LATENCY = 0.10
_WEIGHT_COST = 0.10
_WEIGHT_PREFERENCE = 0.05


# One candidate's score, kept for the audit trail
@dataclass
class CandidateScore:
    agent: AgentManifest
    score: float


# The chosen agent plus every candidate considered, for explainability
@dataclass
class RouterResult:
    selected: AgentManifest
    candidates_evaluated: list[CandidateScore] = field(default_factory=list)
    selection_reason: str = ""


def _score(agent: AgentManifest) -> float:
    latency_score = max(0.0, 1 - agent.estimated_latency_ms / _MAX_LATENCY_MS)
    cost_score = max(0.0, 1 - agent.estimated_cost_units / _MAX_COST_UNITS)
    preference_score = 0.5  # no per-user agent preference signal yet
    return (
        _WEIGHT_CAPABILITY_FIT
        + _WEIGHT_RELIABILITY * agent.reliability_score
        + _WEIGHT_HEALTH * _HEALTH_SCORE[agent.health_status]
        + _WEIGHT_LATENCY * latency_score
        + _WEIGHT_COST * cost_score
        + _WEIGHT_PREFERENCE * preference_score
    )


# Filters the catalogue to eligible agents, then picks the highest scorer
class CapabilityRouter:
    def select(
        self,
        required_capability: str,
        catalogue: list[AgentManifest],
        exclude_ids: list[str] | None = None,
    ) -> RouterResult:
        exclude_ids = exclude_ids or []
        eligible = [
            agent
            for agent in catalogue
            if required_capability in agent.capabilities
            and agent.is_eligible
            and agent.health_status != AgentHealthStatus.UNAVAILABLE
            and agent.implementation_status in _WORKING_IMPLEMENTATION_STATUSES
            and agent.agent_id not in exclude_ids
        ]
        if not eligible:
            raise NoEligibleAgentError(required_capability)

        scored = sorted(
            (CandidateScore(agent=a, score=_score(a)) for a in eligible),
            key=lambda c: c.score,
            reverse=True,
        )
        winner = scored[0]

        return RouterResult(
            selected=winner.agent,
            candidates_evaluated=scored,
            selection_reason=(
                f"Highest score ({winner.score:.3f}): "
                f"reliability={winner.agent.reliability_score}, "
                f"health={winner.agent.health_status.value}"
            ),
        )
