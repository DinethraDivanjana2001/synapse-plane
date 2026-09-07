"""Tool-level exceptions."""


# Raised when a tool call times out or fails, so the router can fall back
class ToolTimeoutError(Exception):
    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"{tool_name} failed: {reason}")
