"""Agent manifest domain model.

Field set follows the v3 manifest schema in docs/AGENT_CATALOGUE.md. Only
manifests with trust_level=approved AND enabled=true may ever be selected
by the router (docs/AGENTS.md section "Agent catalogue rules").
"""

from pydantic import BaseModel, Field

from synapse_plane.domain.enums import (
    AgentHealthStatus,
    AgentImplementationStatus,
    AgentOwnership,
    AgentTrustStatus,
    SideEffectLevel,
)


class AgentManifest(BaseModel):
    agent_id: str
    name: str
    ownership: AgentOwnership
    source_repository: str = ""
    version: str
    description: str
    capabilities: list[str]
    endpoint: str = ""
    protocol: str = "internal"
    input_schema: str = ""
    output_schema: str = ""
    permissions: list[str] = Field(default_factory=list)
    side_effect_level: SideEffectLevel
    trust_status: AgentTrustStatus
    enabled: bool = True
    health_status: AgentHealthStatus = AgentHealthStatus.HEALTHY
    implementation_status: AgentImplementationStatus
    reliability_score: float = Field(default=0.9, ge=0.0, le=1.0)
    estimated_latency_ms: int = 0
    estimated_cost_units: float = 0.0
    timeout_seconds: int = 30
    max_concurrency: int = 1
    tags: list[str] = Field(default_factory=list)

    @property
    def is_eligible(self) -> bool:
        """Deterministic eligibility gate — no other layer may bypass this."""
        return self.enabled and self.trust_status == AgentTrustStatus.APPROVED
