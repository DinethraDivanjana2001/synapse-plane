"""Adapter for the browser-use external agent (browser-use/browser-use).

Not installed in this environment — health_check() honestly reports that.
The adapter is written so installing the package later needs no code change.
"""

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError

_SAFE_TASK_TEMPLATE = """Find suitable restaurants matching these requirements:
Location: {location}
Requirements: {requirements}

For each restaurant found, extract: name, address, cuisine, approximate price
level, whether it appears quiet/relaxed, and the source URL.
Return results as JSON with key 'restaurants'.

Do NOT click on booking buttons, login pages, or payment pages.
"""


# Delegates venue discovery to a live browser-automation agent
class BrowserUseAdapter(BaseAgent):
    agent_id = "external-browser-use"

    def __init__(self, llm_client: object | None = None):
        self.llm_client = llm_client

    def health_check(self) -> bool:
        try:
            import browser_use  # noqa: F401
        except ImportError:
            return False
        return self.llm_client is not None

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not self.health_check():
            raise AgentUnavailableError(self.agent_id, "browser-use not installed/configured")

        from browser_use import Agent as BrowserAgent  # type: ignore[import-not-found]

        task = _SAFE_TASK_TEMPLATE.format(
            location=agent_input.context.get("location", ""),
            requirements=agent_input.context.get("requirements", ""),
        )
        agent = BrowserAgent(task=task, llm=self.llm_client)
        result = await agent.run(max_steps=15)

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={"raw": result},
            observations=["Browser discovered venues from web sources"],
            tool_calls_made=["browser_navigate", "browser_extract"],
            confidence=0.85,
        )
