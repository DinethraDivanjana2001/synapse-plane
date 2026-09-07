"""Adapter for the OpenClaw external agent (self-hosted MCP gateway).

No gateway is configured in this environment — health_check() honestly
reports that (REGISTERED_NOT_CONFIGURED in the catalogue).
"""

import httpx

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError


# Delegates bounded personal-assistant tasks (calendar) to OpenClaw via MCP
class OpenClawAdapter(BaseAgent):
    agent_id = "external-openclaw-personal"

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint

    async def health_check_async(self) -> bool:
        if not self.endpoint:
            return False
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.endpoint}/health")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    def health_check(self) -> bool:
        return bool(self.endpoint)

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not await self.health_check_async():
            raise AgentUnavailableError(self.agent_id, "OpenClaw gateway not reachable")

        task_payload = {
            "goal": agent_input.goal,
            "inputs": agent_input.context.get("task_inputs", {}),
            "permissions": agent_input.permissions,
            "approval_id": agent_input.context.get("approval_id"),
            "idempotency_key": agent_input.context.get("idempotency_key"),
        }
        async with httpx.AsyncClient(timeout=agent_input.timeout_seconds) as client:
            response = await client.post(f"{self.endpoint}/tasks", json=task_payload)
            response.raise_for_status()
            data = response.json()

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=data.get("status") == "completed",
            result=data.get("result", {}),
            observations=data.get("observations", []),
            tool_calls_made=["openclaw_mcp"],
            confidence=0.9,
        )
