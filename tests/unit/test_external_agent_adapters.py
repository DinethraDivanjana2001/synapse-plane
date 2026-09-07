"""Unit tests for external agent adapters — none are installed/configured
in this environment, so health checks must honestly report that."""

import pytest

from synapse_plane.agents.base import AgentInput
from synapse_plane.agents.errors import AgentUnavailableError
from synapse_plane.agents.external.browser_use_adapter import BrowserUseAdapter
from synapse_plane.agents.external.open_deep_research_adapter import OpenDeepResearchAdapter
from synapse_plane.agents.external.openclaw_adapter import OpenClawAdapter


def test_browser_use_health_check_is_false_when_not_installed() -> None:
    assert BrowserUseAdapter().health_check() is False


def test_open_deep_research_health_check_is_false_without_endpoint() -> None:
    assert OpenDeepResearchAdapter().health_check() is False


def test_openclaw_health_check_is_false_without_endpoint() -> None:
    assert OpenClawAdapter().health_check() is False


async def test_browser_use_execute_raises_when_unavailable() -> None:
    with pytest.raises(AgentUnavailableError):
        await BrowserUseAdapter().execute(
            AgentInput(goal="find restaurants", task_id="t1", execution_id="e1", context={})
        )


async def test_open_deep_research_execute_raises_when_unavailable() -> None:
    with pytest.raises(AgentUnavailableError):
        await OpenDeepResearchAdapter().execute(
            AgentInput(goal="research", task_id="t1", execution_id="e1", context={})
        )


async def test_openclaw_execute_raises_when_unavailable() -> None:
    with pytest.raises(AgentUnavailableError):
        await OpenClawAdapter().execute(
            AgentInput(goal="create event", task_id="t1", execution_id="e1", context={})
        )
