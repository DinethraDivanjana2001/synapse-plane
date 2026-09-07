"""Context Intelligence Agent — wraps HybridContextRetriever with agent bookkeeping."""

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.retrieval.context_retriever import HybridContextRetriever


# Interprets the intent, retrieves grounded context, and reports how it did it
class ContextIntelligenceAgent(BaseAgent):
    agent_id = "internal-context-intelligence"

    def __init__(self, retriever: HybridContextRetriever):
        self.retriever = retriever

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        user_id = agent_input.context["user_id"]
        package = await self.retriever.retrieve(agent_input.goal, user_id)

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=package.model_dump(mode="json"),
            observations=[
                f"Scanned {package.total_memories_scanned} memories",
                f"Selected {len(package.items)} within the token budget",
            ],
            tool_calls_made=["semantic_search", "explicit_preferences", "entity_graph"],
            confidence=min(1.0, len(package.items) / 5.0),
        )

    def health_check(self) -> bool:
        return True
