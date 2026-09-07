"""Shared interface every agent (internal or external) implements."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# The bounded input handed to one agent for one task — never the full memory DB
@dataclass
class AgentInput:
    goal: str
    task_id: str
    execution_id: str
    context: dict[str, Any]
    permissions: list[str] = field(default_factory=list)
    timeout_seconds: int = 30


# What an agent reports back after running
@dataclass
class AgentOutput:
    task_id: str
    agent_id: str
    success: bool
    result: dict[str, Any]
    observations: list[str] = field(default_factory=list)
    tool_calls_made: list[str] = field(default_factory=list)
    confidence: float = 0.0
    error: str | None = None


# A goal-directed agent: reasons, chooses tools, observes, adapts
class BaseAgent(ABC):
    agent_id: str

    @abstractmethod
    async def execute(self, agent_input: AgentInput) -> AgentOutput: ...

    @abstractmethod
    def health_check(self) -> bool: ...
