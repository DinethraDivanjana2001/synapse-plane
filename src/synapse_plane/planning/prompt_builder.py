"""Builds the system prompt for the LLM intent planner."""

import json

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.workflow import WorkflowDefinition

SYSTEM_PROMPT_TEMPLATE = """You are the intent planner for SynapsePlane, an agentic system.
Your job is to decompose a user intent into a structured workflow of tasks.

Rules:
- Only use capabilities from the ALLOWED_CAPABILITIES list below
- Never invent capabilities not in that list
- Each task must declare its required_capability, depends_on list, input_bindings, and risk_level
- CONSEQUENTIAL_WRITE tasks require approval_required: true
- Return ONLY valid JSON matching the WorkflowDefinition schema

ALLOWED_CAPABILITIES:
{allowed_capabilities}

USER PROFILE CONTEXT:
{profile_context}

Return JSON matching this schema exactly:
{schema}
"""


# Builds the bounded prompt sent to the LLM — never the full catalogue or history
class PromptBuilder:
    @staticmethod
    def build(profile: UserProfile, catalogue: list[AgentManifest]) -> str:
        allowed_capabilities = sorted({cap for agent in catalogue for cap in agent.capabilities})
        profile_context = {
            "home_location": profile.home_location.label,
            "timezone": profile.timezone,
            "food_preferences": profile.food_preferences.model_dump(),
            "travel_preferences": profile.travel_preferences.model_dump(),
        }
        return SYSTEM_PROMPT_TEMPLATE.format(
            allowed_capabilities=json.dumps(allowed_capabilities, indent=2),
            profile_context=json.dumps(profile_context, indent=2),
            schema=json.dumps(WorkflowDefinition.model_json_schema(), indent=2),
        )
