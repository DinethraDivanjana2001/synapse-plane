"""Agent-level exceptions."""


# Raised when an agent (typically external) cannot be reached or used
class AgentUnavailableError(Exception):
    def __init__(self, agent_id: str, reason: str):
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"{agent_id} unavailable: {reason}")
