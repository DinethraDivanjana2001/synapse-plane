"""Resolves input_bindings like '$tasks.resolve_context.output.location'
into real values from previously completed tasks' outputs."""

from typing import Any


# Turns a task's declared input_bindings into a real input dict
class BindingResolver:
    def resolve(
        self, bindings: dict[str, str], task_outputs: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, binding in bindings.items():
            if not binding.startswith("$tasks."):
                resolved[key] = binding
                continue

            parts = binding.removeprefix("$tasks.").split(".")
            task_id = parts[0]
            field_path = parts[2:] if len(parts) > 1 and parts[1] == "output" else parts[1:]

            value: Any = task_outputs.get(task_id)
            for field in field_path:
                value = value.get(field) if isinstance(value, dict) else None
            resolved[key] = value
        return resolved
