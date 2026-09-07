"""State enums shared across the domain layer."""

from enum import StrEnum


# Overall status of one execution
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


# Status of one task within a workflow
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


# How consequential a task's side effects are
class RiskLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    CONSEQUENTIAL_WRITE = "CONSEQUENTIAL_WRITE"
    PROHIBITED = "PROHIBITED"


# Outcome of one task execution attempt
class AttemptStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


# Category of a stored memory
class MemoryType(StrEnum):
    EXPLICIT_PROFILE = "explicit_profile"
    EPISODIC = "episodic"
    PREFERENCE = "preference"
    GOAL = "goal"
    RELATIONSHIP = "relationship"
    DECISION = "decision"
    OUTCOME = "outcome"


# Whether a memory was stated directly or inferred
class ExplicitOrInferred(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


# Kind of entity in the knowledge graph
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


# Whether an agent is approved for use
class AgentTrustStatus(StrEnum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REVOKED = "revoked"


# How complete an agent's integration is
class AgentImplementationStatus(StrEnum):
    FULLY_IMPLEMENTED = "FULLY_IMPLEMENTED"
    LIVE_EXTERNAL = "LIVE_EXTERNAL"
    CONFIGURED = "CONFIGURED"
    REGISTERED_NOT_CONFIGURED = "REGISTERED_NOT_CONFIGURED"
    PLANNED = "PLANNED"
    MOCK = "mock"
    CATALOGUE_ONLY = "catalogue_only"
    DISABLED = "disabled"


# Whether an agent is built in-house or third-party
class AgentOwnership(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


# How much an agent's actions can affect the outside world
class SideEffectLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    MIXED = "MIXED"
    CONSEQUENTIAL_WRITE = "CONSEQUENTIAL_WRITE"
    NONE = "NONE"


# Current health of an agent
class AgentHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


# Classification of why a task attempt failed
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


# Status of a human approval request
class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
