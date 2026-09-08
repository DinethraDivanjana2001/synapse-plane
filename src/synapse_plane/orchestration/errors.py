"""Orchestration-level exceptions."""


# Raised to pause a task at the approval gate; propagates up to the scheduler
class ApprovalRequiredError(Exception):
    def __init__(self, proposal_id: str):
        self.proposal_id = proposal_id
        super().__init__(f"Approval required: {proposal_id}")
