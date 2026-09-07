"""Deterministic plan validation — the LLM cannot bypass this."""

import graphlib
from dataclasses import dataclass, field

from synapse_plane.domain.agent import AgentManifest
from synapse_plane.domain.workflow import WorkflowDefinition

# Hardcoded, never derived from the catalogue — no agent can ever offer these
PROHIBITED_CAPABILITIES = {
    "payment.execute",
    "flight.book",
    "hotel.book",
    "restaurant.reserve",
    "message.send_external",
    "account.modify",
    "file.delete_external",
}


# Result of validating one plan: pass/fail plus every error found
@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


# Rejects plans with unknown/prohibited capabilities, bad references, or cycles
class PlanValidator:
    def validate(
        self, plan: WorkflowDefinition, catalogue: list[AgentManifest]
    ) -> ValidationResult:
        errors: list[str] = []
        task_ids = {t.task_id for t in plan.tasks}
        known_capabilities = {cap for agent in catalogue for cap in agent.capabilities}

        if len(task_ids) != len(plan.tasks):
            errors.append("Duplicate task IDs found")

        for task in plan.tasks:
            if task.required_capability in PROHIBITED_CAPABILITIES:
                errors.append(
                    f"Task {task.task_id} uses prohibited capability: {task.required_capability}"
                )
            elif task.required_capability not in known_capabilities:
                errors.append(
                    f"Task {task.task_id} uses unknown capability: {task.required_capability}"
                )

            for dep in task.depends_on:
                if dep not in task_ids:
                    errors.append(f"Task {task.task_id} depends on unknown task: {dep}")

            for key, binding in task.input_bindings.items():
                if binding.startswith("$tasks."):
                    ref_task = binding.split(".")[1]
                    if ref_task not in task_ids:
                        errors.append(
                            f"Task {task.task_id} binding '{key}' references "
                            f"unknown task: {ref_task}"
                        )

        if not errors:
            graph = {t.task_id: set(t.depends_on) for t in plan.tasks}
            try:
                list(graphlib.TopologicalSorter(graph).static_order())
            except graphlib.CycleError as e:
                errors.append(f"Cyclic dependency detected: {e}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)
