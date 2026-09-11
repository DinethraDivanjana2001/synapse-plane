"""Decides which tasks need human approval and builds the signed proposal."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from synapse_plane.domain.enums import RiskLevel
from synapse_plane.domain.execution import ApprovalProposal
from synapse_plane.domain.profile import UserProfile
from synapse_plane.domain.workflow import TaskDefinition

_PROPOSAL_TTL_HOURS = 24

# The exact fields the action digest is computed over — read off an already
# Pydantic-validated ApprovalProposal, never off the raw pre-validation dict.
# That's what makes build_proposal's digest and verify_digest's recomputed
# digest guaranteed to agree: both hash the same typed object shape,
# datetimes included, via the same isoformat() serialization.
_DIGESTED_FIELDS = (
    "restaurant_name",
    "address",
    "start_time",
    "end_time",
    "timezone",
    "calendar_id",
    "description",
    "tool_identifier",
)


def _compute_digest(proposal: ApprovalProposal) -> str:
    fields = {}
    for name in _DIGESTED_FIELDS:
        value = getattr(proposal, name)
        fields[name] = value.isoformat() if isinstance(value, datetime) else value
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


# Gate for CONSEQUENTIAL_WRITE tasks — nothing external happens without this
class ApprovalPolicy:
    def requires_approval(self, task: TaskDefinition) -> bool:
        return task.risk_level == RiskLevel.CONSEQUENTIAL_WRITE

    def is_prohibited(self, task: TaskDefinition) -> bool:
        return task.risk_level == RiskLevel.PROHIBITED

    def build_proposal(
        self,
        execution_id: str,
        task_id: str,
        recommendation: dict,
        time_slot: dict,
        profile: UserProfile,
        context_package_id: str | None = None,
    ) -> ApprovalProposal:
        selected = recommendation.get("selected", recommendation)
        fields = {
            "restaurant_name": selected.get("name", "Unknown"),
            "address": selected.get("address", ""),
            "start_time": time_slot["start_time"],
            "end_time": time_slot["end_time"],
            "timezone": profile.timezone,
            "calendar_id": profile.calendar.calendar_id,
            "description": f"Dinner at {selected.get('name', 'Unknown')}",
            "tool_identifier": "calendar_write_tool.create_event",
        }
        now = datetime.now(UTC)

        # action_digest is computed below from the constructed proposal
        # itself, not from `fields` — placeholder value here is overwritten
        # before this proposal is ever persisted or returned.
        proposal = ApprovalProposal(
            proposal_id=str(uuid4()),
            execution_id=execution_id,
            task_id=task_id,
            context_package_id=context_package_id,
            action_digest="",
            created_at=now,
            expires_at=now + timedelta(hours=_PROPOSAL_TTL_HOURS),
            **fields,
        )
        return proposal.model_copy(update={"action_digest": _compute_digest(proposal)})

    def is_expired(self, proposal: ApprovalProposal, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        expires_at = proposal.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return now > expires_at

    def verify_digest(self, proposal: ApprovalProposal) -> bool:
        """Recomputes the digest from the proposal's own stored fields and
        compares it to action_digest — catches a proposal row altered after
        creation without also updating its digest."""
        return _compute_digest(proposal) == proposal.action_digest
