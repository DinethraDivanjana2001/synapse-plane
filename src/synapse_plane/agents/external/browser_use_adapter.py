"""Venue discovery — Tavily search + Gemini extraction.

Standing in for live browser-use automation: no Playwright/Chromium install
in this environment. Documented substitution, not a claim of live browsing —
see docs/DECISIONS.md. Same agent_id as the catalogue entry either way.
"""

import json

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError
from synapse_plane.domain.tools import RestaurantCandidate
from synapse_plane.tools.search_client import SearchClientProtocol

_EXTRACTION_PROMPT = """Extract restaurants from these web search results.
Return JSON: {{"restaurants": [{{"name": str, "address": str, "cuisine": str,
"rating": float (0.0-5.0, estimate 4.0 if unknown), "price_level": "cheap" or
"moderate" or "expensive", "is_quiet": bool (guess from the description),
"distance_km": float (estimate 2.0 if unknown)}}]}}
Only include actual restaurants that appear in the results below.

Search results:
{results}
"""

_VERIFICATION_PROMPT = """Verify and summarize practical, current details relevant to
this goal, using only the search results below.
Goal: {goal}

Search results:
{results}

Return JSON: {{"summary": str, "details": [str, ...], "sources": [str, ...] (URLs used)}}
"""


# Discovers and verifies restaurant candidates via web search + LLM extraction
class BrowserUseAdapter(BaseAgent):
    agent_id = "external-browser-use"

    def __init__(
        self,
        search_client: SearchClientProtocol | None = None,
        llm_client: object | None = None,
        llm_model: str = "gemini-3.5-flash-lite",
    ):
        self.search_client = search_client
        self.llm_client = llm_client
        self.llm_model = llm_model

    def health_check(self) -> bool:
        return self.search_client is not None and self.llm_client is not None

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not self.health_check():
            raise AgentUnavailableError(self.agent_id, "search/LLM client not configured")

        if agent_input.required_capability == "web.verify_information":
            return await self._verify_information(agent_input)
        return await self._discover_places(agent_input)

    async def _verify_information(self, agent_input: AgentInput) -> AgentOutput:
        # This capability serves the travel use case's "verify practical
        # details" step — the goal (the task's own description, written by
        # the planner) names the actual destinations, unlike the discovery
        # capability which reads a separate location/requirements binding.
        goal = agent_input.goal
        results = await self.search_client.search(goal, max_results=6)  # type: ignore[union-attr]
        results_text = "\n".join(f"- {r.title}: {r.content[:400]} ({r.url})" for r in results)

        response = await self.llm_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": _VERIFICATION_PROMPT.format(goal=goal, results=results_text),
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        details = json.loads(response.choices[0].message.content)

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=details,
            observations=[f"Verified '{goal}' across {len(results)} sources"],
            tool_calls_made=["tavily_search", "llm_verify"],
            confidence=0.7 if results else 0.2,
        )

    async def _discover_places(self, agent_input: AgentInput) -> AgentOutput:
        location = agent_input.context.get("location", "")
        requirements = agent_input.context.get("requirements", "")
        query = f"best {requirements} restaurants in {location}".strip()
        results = await self.search_client.search(query, max_results=5)  # type: ignore[union-attr]

        results_text = "\n".join(f"- {r.title}: {r.content[:500]} ({r.url})" for r in results)
        response = await self.llm_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.llm_model,
            messages=[{"role": "user", "content": _EXTRACTION_PROMPT.format(results=results_text)}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        parsed = json.loads(response.choices[0].message.content)

        candidates: list[RestaurantCandidate] = []
        for raw in parsed.get("restaurants", []):
            try:
                candidates.append(RestaurantCandidate(**raw, source="tavily_search"))
            except (TypeError, ValueError):
                continue  # skip malformed LLM output rather than fail the whole task

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={"candidates": [c.model_dump(mode="json") for c in candidates]},
            observations=[f"Searched web for '{query}', found {len(results)} sources"],
            tool_calls_made=["tavily_search", "llm_extract"],
            confidence=0.7 if candidates else 0.2,
        )
