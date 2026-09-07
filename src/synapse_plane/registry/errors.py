"""Registry-level exceptions."""


# Raised when no eligible agent offers a required capability
class NoEligibleAgentError(Exception):
    def __init__(self, capability: str):
        self.capability = capability
        super().__init__(f"No eligible agent offers capability: {capability}")
