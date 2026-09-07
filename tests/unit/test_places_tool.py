"""Unit tests for PlacesTool / PlacesFallbackTool — pure, no DB, no LLM."""

import pytest

from synapse_plane.domain.tools import RestaurantSearchRequest
from synapse_plane.tools.errors import ToolTimeoutError
from synapse_plane.tools.places_tool import PlacesFallbackTool, PlacesTool


async def test_search_returns_matching_cuisine() -> None:
    request = RestaurantSearchRequest(location_label="Colombo", cuisines=["japanese"])
    results = await PlacesTool().search(request)
    assert all(r.cuisine == "japanese" for r in results)


async def test_search_with_no_cuisine_filter_returns_all() -> None:
    results = await PlacesTool().search(RestaurantSearchRequest(location_label="Colombo"))
    assert len(results) > 1


async def test_inject_failure_raises_tool_timeout() -> None:
    with pytest.raises(ToolTimeoutError):
        await PlacesTool().search(
            RestaurantSearchRequest(location_label="Colombo"), inject_failure=True
        )


async def test_fallback_tool_always_succeeds() -> None:
    results = await PlacesFallbackTool().search(RestaurantSearchRequest(location_label="Colombo"))
    assert len(results) >= 1
