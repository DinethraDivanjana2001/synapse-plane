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
        action_digest = hashlib.sha256(
            json.dumps(fields, sort_keys=True, default=str).encode()
        ).hexdigest()
        now = datetime.now(UTC)

        return ApprovalProposal(
            proposal_id=str(uuid4()),
            execution_id=execution_id,
            task_id=task_id,
            context_package_id=context_package_id,
            action_digest=action_digest,
            created_at=now,
            expires_at=now + timedelta(hours=_PROPOSAL_TTL_HOURS),
            **fields,
        )
