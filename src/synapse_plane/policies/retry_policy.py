"""Classifies task failures and decides whether to retry, fall back, or stop."""

from synapse_plane.agents.errors import AgentUnavailableError
from synapse_plane.domain.enums import FailureClass
from synapse_plane.tools.errors import ToolTimeoutError

MAX_RETRIES = 2
MAX_BACKOFF_SECONDS = 30
_RETRYABLE = {FailureClass.TRANSIENT, FailureClass.RATE_LIMITED}
_FALLBACK_ELIGIBLE = {FailureClass.AGENT_UNAVAILABLE, FailureClass.TRANSIENT}


# Deterministic failure handling — no LLM decides retry/fallback/stop
class RetryPolicy:
    def classify_failure(self, error: Exception) -> FailureClass:
        if isinstance(error, ToolTimeoutError):
            return FailureClass.TRANSIENT
        if isinstance(error, AgentUnavailableError):
            return FailureClass.AGENT_UNAVAILABLE
        return FailureClass.TERMINAL

    def should_retry(self, failure_class: FailureClass, attempt_number: int) -> bool:
        return attempt_number < MAX_RETRIES and failure_class in _RETRYABLE

    def backoff_seconds(self, attempt_number: int) -> float:
        return min(2**attempt_number, MAX_BACKOFF_SECONDS)

    def should_fallback(self, failure_class: FailureClass) -> bool:
        return failure_class in _FALLBACK_ELIGIBLE
