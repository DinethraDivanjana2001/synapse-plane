"""Multi-source destination research — Tavily search + Gemini synthesis.

No LangGraph server is running in this environment; this implements the
research step directly (search, then synthesize) rather than delegating to
a separately-hosted open_deep_research server.
"""

import json

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError
from synapse_plane.tools.search_client import SearchClientProtocol

_SYNTHESIS_PROMPT = """Answer this research goal using only the sources below.
Goal: {goal}

Sources:
{results}

Return JSON: {{"summary": str, "findings": [str, ...], "sources": [str, ...] (URLs used)}}
"""


# Plans and runs multi-step research, synthesizing an evidence-backed report
class OpenDeepResearchAdapter(BaseAgent):
    agent_id = "external-open-deep-research"

    def __init__(
        self,
        search_client: SearchClientProtocol | None = None,
        llm_client: object | None = None,
        llm_model: str = "gemini-1.5-flash",
    ):
        self.search_client = search_client
        self.llm_client = llm_client
        self.llm_model = llm_model

    def health_check(self) -> bool:
        return self.search_client is not None and self.llm_client is not None

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not self.health_check():
            raise AgentUnavailableError(self.agent_id, "search/LLM client not configured")

        goal = agent_input.goal
        results = await self.search_client.search(goal, max_results=8)  # type: ignore[union-attr]
        results_text = "\n".join(f"- {r.title}: {r.content[:300]} ({r.url})" for r in results)

        response = await self.llm_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": _SYNTHESIS_PROMPT.format(goal=goal, results=results_text),
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        report = json.loads(response.choices[0].message.content)

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=report,
            observations=[f"Researched '{goal}' across {len(results)} sources"],
            tool_calls_made=["tavily_search", "llm_synthesize"],
            confidence=0.75 if results else 0.2,
        )
