"""Planning-specific exceptions."""


# Raised when an intent requires a capability the system will never provide
class UnsupportedCapabilityError(Exception):
    def __init__(self, capabilities: list[str]):
        self.capabilities = capabilities
        super().__init__(f"Unsupported capabilities: {', '.join(capabilities)}")
