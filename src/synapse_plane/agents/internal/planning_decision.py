"""Planning & Decision Agent — proposes plans and ranks/recommends candidates.

Proposes only. Deterministic PlanValidator approves or rejects what it
produces; the recommendation score itself is also deterministic — only the
optional explanation text may come from an LLM.
"""

import json
from typing import Protocol

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.tools import RestaurantCandidate
from synapse_plane.domain.workflow import WorkflowDefinition

_COMPARISON_PROMPT = """Compare these travel destinations and recommend exactly one,
using only the research, verified details, and weather below. Be specific about why —
if one destination has a much higher chance of rain, that should factor into your
recommendation, not just the attractions.

Research:
{research}

Verified details:
{details}

Weather forecast:
{weather}

Return JSON: {{"selected_destination": str, "reasoning": str}}
"""


# Interface both IntentPlanner (real) and FakePlanner (tests) satisfy
class PlannerProtocol(Protocol):
    async def plan(
        self,
        intent: str,
        profile: UserProfile,
        catalogue: list[AgentManifest],
        relevant_facts: list[str] | None = None,
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

    def __init__(
        self,
        planner: PlannerProtocol,
        llm_client: object | None = None,
        llm_model: str = "gemini-3.5-flash-lite",
    ):
        self.planner = planner
        self.llm_client = llm_client
        self.llm_model = llm_model

    async def plan(
        self, intent: str, profile: UserProfile, catalogue: list[AgentManifest]
    ) -> WorkflowDefinition:
        return await self.planner.plan(intent, profile, catalogue)

    def recommend(
        self, candidates: list[RestaurantCandidate], preferred_cuisines: list[str]
    ) -> RestaurantCandidate:
        if not candidates:
            raise ValueError("no restaurant candidates to recommend from")
        return max(candidates, key=lambda c: score_candidate(c, preferred_cuisines))

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if agent_input.required_capability == "alternatives.compare":
            return await self._compare_alternatives(agent_input)

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

    async def _compare_alternatives(self, agent_input: AgentInput) -> AgentOutput:
        """Travel destination comparison. With an LLM client (real mode),
        Gemini writes the justification from the research/details text. With
        none (demo mode — never a live call), falls back to a deterministic
        score against the profile's own travel interests, over the canned
        destinations dict DemoResearchAgent/DemoVenueDiscoveryAgent produced."""
        research = agent_input.context.get("research", {})
        details = agent_input.context.get("details", {})
        weather = agent_input.context.get("weather", {})

        if self.llm_client is not None:
            response = await self.llm_client.chat.completions.create(  # type: ignore[attr-defined]
                model=self.llm_model,
                messages=[
                    {
                        "role": "user",
                        "content": _COMPARISON_PROMPT.format(
                            research=json.dumps(research),
                            details=json.dumps(details),
                            weather=json.dumps(weather),
                        ),
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            result = json.loads(response.choices[0].message.content)
            tool_calls = ["llm_compare"]
            confidence = 0.75
        else:
            destinations = research.get("destinations", {})
            interests = set(agent_input.context.get("travel_interests", []))
            forecasts = weather.get("forecasts", {})
            if destinations:
                # Interest match first, then break ties toward the drier
                # forecast — a real factor, not just attractions on paper.
                def _rank(item: tuple[str, dict]) -> tuple[int, int]:
                    key, dest = item
                    interest_score = len(interests & set(dest.get("best_for", [])))
                    rain_pct = forecasts.get(key, {}).get("precipitation_probability", 50)
                    return (interest_score, -rain_pct)

                best_key, best = max(destinations.items(), key=_rank)
                best_for = ", ".join(best.get("best_for", []))
                advisory = details.get("details", {}).get(best_key, "")
                forecast = forecasts.get(best_key, {})
                weather_note = (
                    f" Forecast: {forecast.get('condition')}, "
                    f"{forecast.get('precipitation_probability')}% chance of rain."
                    if forecast
                    else ""
                )
                reasoning = f"Best matches your interests in {best_for}. {advisory}{weather_note}"
                result = {"selected_destination": best["name"], "reasoning": reasoning}
            else:
                result = {"selected_destination": "unknown", "reasoning": "No destinations found"}
            tool_calls = ["score_destination"]
            confidence = 0.8

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=result,
            observations=[f"Compared destinations, selected {result.get('selected_destination')}"],
            tool_calls_made=tool_calls,
            confidence=confidence,
        )

    def health_check(self) -> bool:
        return True
