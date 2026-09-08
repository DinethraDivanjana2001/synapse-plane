"""Restaurant search tools — deterministic mock data, no live API (ADR-007)."""

from synapse_plane.domain.tools import RestaurantCandidate, RestaurantSearchRequest
from synapse_plane.tools.errors import ToolTimeoutError

MOCK_RESTAURANTS = [
    RestaurantCandidate(
        name="La Foresta",
        address="14 Flower Road, Colombo 07",
        cuisine="italian",
        rating=4.6,
        price_level="moderate",
        is_quiet=True,
        distance_km=2.1,
        source="places_primary_tool",
    ),
    RestaurantCandidate(
        name="Bella Roma",
        address="88 Galle Road, Colombo 03",
        cuisine="italian",
        rating=4.1,
        price_level="moderate",
        is_quiet=False,
        distance_km=1.4,
        source="places_primary_tool",
    ),
    RestaurantCandidate(
        name="Sakura Garden",
        address="22 Duplication Road, Colombo 05",
        cuisine="japanese",
        rating=4.4,
        price_level="expensive",
        is_quiet=True,
        distance_km=3.8,
        source="places_primary_tool",
    ),
    RestaurantCandidate(
        name="Colombo Spice House",
        address="5 Marine Drive, Colombo 03",
        cuisine="sri_lankan",
        rating=4.3,
        price_level="cheap",
        is_quiet=False,
        distance_km=0.9,
        source="places_primary_tool",
    ),
]

MOCK_RESTAURANTS_FALLBACK = [
    RestaurantCandidate(
        name="The Quiet Table",
        address="3 Barnes Place, Colombo 07",
        cuisine="italian",
        rating=4.2,
        price_level="moderate",
        is_quiet=True,
        distance_km=2.7,
        source="places_fallback_tool",
    ),
]


# Primary restaurant search — one operation, no reasoning
class PlacesTool:
    async def search(
        self, request: RestaurantSearchRequest, inject_failure: bool = False
    ) -> list[RestaurantCandidate]:
        if inject_failure:
            raise ToolTimeoutError("places_primary_tool", "Simulated timeout")
        if not request.cuisines:
            return list(MOCK_RESTAURANTS)
        return [c for c in MOCK_RESTAURANTS if c.cuisine in request.cuisines] or list(
            MOCK_RESTAURANTS
        )


# Fallback restaurant search — always succeeds, used when PlacesTool fails
class PlacesFallbackTool:
    async def search(self, request: RestaurantSearchRequest) -> list[RestaurantCandidate]:  # noqa: ARG002
        return list(MOCK_RESTAURANTS_FALLBACK)
