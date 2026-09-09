"""Real LLM-backed intent planner — OpenAI JSON mode."""

from synapse_plane.config import Settings
from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.workflow import WorkflowDefinition
from synapse_plane.planning.prompt_builder import PromptBuilder


# Proposes a WorkflowDefinition from a natural-language intent; never executes it
class IntentPlanner:
    def __init__(self, llm_client: object, settings: Settings):
        self.llm_client = llm_client
        self.settings = settings

    async def plan(
        self,
        intent: str,
        profile: UserProfile,
        catalogue: list[AgentManifest],
        relevant_facts: list[str] | None = None,
    ) -> WorkflowDefinition:
        system_prompt = PromptBuilder.build(profile, catalogue, relevant_facts)

        response = await self.llm_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Intent: {intent}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return WorkflowDefinition.model_validate_json(response.choices[0].message.content)
