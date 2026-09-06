"""State enums shared across the domain layer.

These are the only vocabulary allowed for execution/task state, risk
classification, memory typing, and agent trust/health. No other layer may
invent new string values for these concepts.
"""

from enum import StrEnum


class ExecutionStatus(StrEnum):
    RECEIVED = "RECEIVED"
    CONTEXT_RETRIEVAL = "CONTEXT_RETRIEVAL"
    PLANNING = "PLANNING"
    PLAN_VALIDATION = "PLAN_VALIDATION"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RESUMING = "RESUMING"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class RiskLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    CONSEQUENTIAL_WRITE = "CONSEQUENTIAL_WRITE"
    PROHIBITED = "PROHIBITED"


class AttemptStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class MemoryType(StrEnum):
    EXPLICIT_PROFILE = "explicit_profile"
    EPISODIC = "episodic"
    PREFERENCE = "preference"
    GOAL = "goal"
    RELATIONSHIP = "relationship"
    DECISION = "decision"
    OUTCOME = "outcome"


class ExplicitOrInferred(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class EntityType(StrEnum):
    USER = "user"
    PERSON = "person"
    PLACE = "place"
    RESTAURANT = "restaurant"
    GOAL = "goal"
    PREFERENCE = "preference"
    EVENT = "event"
    TASK = "task"
    DECISION = "decision"
    TOPIC = "topic"
    ORGANIZATION = "organization"


class AgentTrustStatus(StrEnum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REVOKED = "revoked"


class AgentImplementationStatus(StrEnum):
    FULLY_IMPLEMENTED = "FULLY_IMPLEMENTED"
    LIVE_EXTERNAL = "LIVE_EXTERNAL"
    CONFIGURED = "CONFIGURED"
    REGISTERED_NOT_CONFIGURED = "REGISTERED_NOT_CONFIGURED"
    PLANNED = "PLANNED"
    MOCK = "mock"
    CATALOGUE_ONLY = "catalogue_only"
    DISABLED = "disabled"


class AgentOwnership(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class SideEffectLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    MIXED = "MIXED"
    CONSEQUENTIAL_WRITE = "CONSEQUENTIAL_WRITE"
    NONE = "NONE"


class AgentHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class FailureClass(StrEnum):
    TRANSIENT = "TRANSIENT"
    RATE_LIMITED = "RATE_LIMITED"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    NO_RESULTS = "NO_RESULTS"
    MISSING_INFO = "MISSING_INFO"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    TERMINAL = "TERMINAL"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
