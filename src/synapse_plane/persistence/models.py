"""SQLAlchemy ORM models: memory/entity/embedding layer + execution layer."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from synapse_plane.persistence.types import EmbeddingVector


class Base(DeclarativeBase):
    # datetime columns are timezone-aware (app always writes UTC-aware values)
    type_annotation_map = {datetime: DateTime(timezone=True)}


# ── Memory / entity / retrieval layer ────────────────────────────────────


# A single stored memory (raw text + metadata)
class MemoryModel(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    memory_type: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float]
    explicit_or_inferred: Mapped[str] = mapped_column(String)
    valid_from: Mapped[datetime]
    valid_to: Mapped[datetime | None]
    supersedes_fact_id: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime]
    observed_at: Mapped[datetime]


# Vector embedding for one memory, used for semantic search
class MemoryEmbeddingModel(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"))
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector)
    model_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime]


# A named person/place/thing extracted from memories
class EntityModel(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    canonical_name: Mapped[str] = mapped_column(String, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime]


# A directed edge between two entities (e.g. User PREFERS QuietRestaurants)
class RelationshipModel(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    relationship_type: Mapped[str] = mapped_column(String)
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    weight: Mapped[float] = mapped_column(default=1.0)
    valid_from: Mapped[datetime]
    valid_to: Mapped[datetime | None]
    source_memory_id: Mapped[str | None] = mapped_column(ForeignKey("memories.id"))


# Links a memory to an entity it mentions
class MemoryEntityModel(Base):
    __tablename__ = "memory_entities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"))
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    role: Mapped[str] = mapped_column(String)


# A log of one hybrid-retrieval call for an execution
class ContextRetrievalModel(Base):
    __tablename__ = "context_retrievals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"))
    intent: Mapped[str] = mapped_column(Text)
    context_package_json: Mapped[str] = mapped_column(Text)
    memories_scanned: Mapped[int]
    items_returned: Mapped[int]
    token_estimate: Mapped[int]
    retrieved_at: Mapped[datetime]


# ── Agent catalogue ───────────────────────────────────────────────────────


# One entry in the agent catalogue (capabilities, trust, health, etc.)
class AgentManifestModel(Base):
    __tablename__ = "agent_manifests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    ownership: Mapped[str] = mapped_column(String)
    source_repository: Mapped[str] = mapped_column(String, default="")
    version: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    capabilities_json: Mapped[str] = mapped_column(Text)
    endpoint: Mapped[str] = mapped_column(String, default="")
    protocol: Mapped[str] = mapped_column(String, default="internal")
    input_schema: Mapped[str] = mapped_column(String, default="")
    output_schema: Mapped[str] = mapped_column(String, default="")
    permissions_json: Mapped[str] = mapped_column(Text, default="[]")
    side_effect_level: Mapped[str] = mapped_column(String)
    trust_status: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(default=True)
    health_status: Mapped[str] = mapped_column(String, default="healthy")
    implementation_status: Mapped[str] = mapped_column(String)
    reliability_score: Mapped[float] = mapped_column(default=0.9)
    estimated_latency_ms: Mapped[int] = mapped_column(default=0)
    estimated_cost_units: Mapped[float] = mapped_column(default=0.0)
    timeout_seconds: Mapped[int] = mapped_column(default=30)
    max_concurrency: Mapped[int] = mapped_column(default=1)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")


# ── Execution layer ───────────────────────────────────────────────────────


# The demo user's profile (stored as JSON, one row per user)
class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String)
    profile_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


# One user intent being executed, with its overall status
class ExecutionModel(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    intent_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="RECEIVED")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


# One planned/re-planned task DAG version for an execution
class WorkflowVersionModel(Base):
    __tablename__ = "workflow_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"))
    planning_version: Mapped[int]
    workflow_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime]


# One task within a workflow version, and its current state
class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"))
    workflow_version_id: Mapped[str] = mapped_column(ForeignKey("workflow_versions.id"))
    task_definition_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    selected_agent_id: Mapped[str | None] = mapped_column(String)
    output_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


# A depends-on edge between two tasks
class TaskDependencyModel(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    depends_on_task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))


# One execution attempt of a task by a specific agent
class TaskAttemptModel(Base):
    __tablename__ = "task_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    attempt_number: Mapped[int]
    agent_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    failure_class: Mapped[str | None] = mapped_column(String)
    output_json: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]


# A human-approval request/decision for a consequential task
class ApprovalModel(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    proposal_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created_at: Mapped[datetime]
    decided_at: Mapped[datetime | None]
    expires_at: Mapped[datetime]


# One entry in an execution's audit/event timeline
class ExecutionEventModel(Base):
    __tablename__ = "execution_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    task_id: Mapped[str | None] = mapped_column(String)
    agent_id: Mapped[str | None] = mapped_column(String)
    attempt_id: Mapped[str | None] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime]


# A record of one tool call made during a task attempt
class ToolInvocationModel(Base):
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_attempt_id: Mapped[str] = mapped_column(ForeignKey("task_attempts.id"))
    tool_identifier: Mapped[str] = mapped_column(String)
    input_json: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String, index=True)
    invoked_at: Mapped[datetime]


# A completed external write, keyed by idempotency key
class ExternalActionRecordModel(Base):
    __tablename__ = "external_action_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String)
    provider_reference_id: Mapped[str] = mapped_column(String)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime]
