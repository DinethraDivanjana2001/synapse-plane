"""Planning & Decision Agent — proposes plans and ranks/recommends candidates.

Proposes only. Deterministic PlanValidator approves or rejects what it
produces; the recommendation score itself is also deterministic — only the
optional explanation text may come from an LLM.
"""

from typing import Protocol

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.tools import RestaurantCandidate
from synapse_plane.domain.workflow import WorkflowDefinition


# Interface both IntentPlanner (real) and FakePlanner (tests) satisfy
class PlannerProtocol(Protocol):
    async def plan(
        self, intent: str, profile: UserProfile, catalogue: list[AgentManifest]
    ) -> WorkflowDefinition: ...


def score_candidate(candidate: RestaurantCandidate, preferred_cuisines: list[str]) -> float:
    """Deterministic ranking — no LLM. Rewards rating, quiet venues, and cuisine match."""
    cuisine_match = 1.0 if candidate.cuisine in preferred_cuisines else 0.0
    return (
        0.5 * (candidate.rating / 5.0)
        + 0.3 * (1.0 if candidate.is_quiet else 0.0)
        + 0.2 * cuisine_match
    )


# Proposes the task DAG and ranks/recommends among candidate results
class PlanningDecisionAgent(BaseAgent):
    agent_id = "internal-planning-decision"

    def __init__(self, planner: PlannerProtocol):
        self.planner = planner

    async def plan(
        self, intent: str, profile: UserProfile, catalogue: list[AgentManifest]
    ) -> WorkflowDefinition:
        return await self.planner.plan(intent, profile, catalogue)

    def recommend(
        self, candidates: list[RestaurantCandidate], preferred_cuisines: list[str]
    ) -> RestaurantCandidate:
        return max(candidates, key=lambda c: score_candidate(c, preferred_cuisines))

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        candidates = [RestaurantCandidate(**c) for c in agent_input.context.get("candidates", [])]
        preferred_cuisines = agent_input.context.get("preferred_cuisines", [])
        top = self.recommend(candidates, preferred_cuisines)

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={"selected": top.model_dump(mode="json")},
            observations=[f"Ranked {len(candidates)} candidates, selected {top.name}"],
            tool_calls_made=["score_candidate"],
            confidence=score_candidate(top, preferred_cuisines),
        )

    def health_check(self) -> bool:
        return True
