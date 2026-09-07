"""Adapter for the Open Deep Research external agent (LangGraph server).

No server is configured in this environment — health_check() honestly
reports that (REGISTERED_NOT_CONFIGURED in the catalogue).
"""

import httpx

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError


# Delegates multi-source destination research to a LangGraph research agent
class OpenDeepResearchAdapter(BaseAgent):
    agent_id = "external-open-deep-research"

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint

    def health_check(self) -> bool:
        return bool(self.endpoint)

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not self.health_check():
            raise AgentUnavailableError(self.agent_id, "no LangGraph server endpoint configured")

        async with httpx.AsyncClient(timeout=agent_input.timeout_seconds) as client:
            response = await client.post(
                f"{self.endpoint}/research",
                json={"goal": agent_input.goal, "context": agent_input.context},
            )
            response.raise_for_status()
            data = response.json()

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=data,
            observations=["Multi-source research completed"],
            tool_calls_made=["langgraph_research"],
            confidence=0.8,
        )
