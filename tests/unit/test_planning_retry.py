"""Retry-with-backoff around the planning call itself — separate from, and
upstream of, task-level retry/fallback. Before this, a single transient LLM
error (timeout, rate limit, provider outage) failed the whole execution on
the first attempt, with no recovery at all."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from apps.api.routes import executions as executions_module
from apps.api.routes.executions import _plan_with_retry
from openai import APIConnectionError, RateLimitError


class FakeEmitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    # execution_id unused — matches EventEmitter's real signature
    async def emit(self, execution_id: str, event_type: str, **payload: object) -> None:  # noqa: ARG002
        self.events.append((event_type, payload))


def _connection_error() -> APIConnectionError:
    return APIConnectionError(request=httpx.Request("POST", "https://example.test"))


def _rate_limit_error() -> RateLimitError:
    response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
    return RateLimitError("rate limited", response=response, body=None)


class FakePlanner:
    def __init__(self, side_effects: list[object]):
        self.side_effects = list(side_effects)
        self.calls = 0

    async def plan(self, intent, profile, catalogue, relevant_facts):  # noqa: ARG002
        self.calls += 1
        effect = self.side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


@pytest.mark.asyncio
async def test_succeeds_immediately_with_no_retry_needed():
    planner = FakePlanner(["a real plan"])
    emitter = FakeEmitter()

    result = await _plan_with_retry(planner, "intent", None, [], [], emitter, "exec-1")

    assert result == "a real plan"
    assert planner.calls == 1
    assert emitter.events == []


@pytest.mark.asyncio
async def test_retries_a_transient_error_then_succeeds():
    planner = FakePlanner([_rate_limit_error(), "a real plan"])
    emitter = FakeEmitter()

    with patch.object(executions_module.asyncio, "sleep", new=AsyncMock()) as sleep:
        result = await _plan_with_retry(planner, "intent", None, [], [], emitter, "exec-1")

    assert result == "a real plan"
    assert planner.calls == 2
    assert sleep.await_count == 1
    assert [e for e, _ in emitter.events] == ["planning.retry_scheduled"]


@pytest.mark.asyncio
async def test_gives_up_after_max_retries_and_raises_the_last_error():
    planner = FakePlanner([_connection_error(), _connection_error(), _connection_error()])
    emitter = FakeEmitter()

    with (
        patch.object(executions_module.asyncio, "sleep", new=AsyncMock()),
        pytest.raises(APIConnectionError),
    ):
        await _plan_with_retry(planner, "intent", None, [], [], emitter, "exec-1")

    assert planner.calls == executions_module.MAX_RETRIES


@pytest.mark.asyncio
async def test_a_non_transient_error_is_not_retried_at_all():
    planner = FakePlanner([ValueError("malformed JSON from the model")])
    emitter = FakeEmitter()

    with pytest.raises(ValueError):
        await _plan_with_retry(planner, "intent", None, [], [], emitter, "exec-1")

    assert planner.calls == 1
    assert emitter.events == []
