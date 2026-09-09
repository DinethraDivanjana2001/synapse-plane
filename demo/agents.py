"""Deterministic demo/test stand-in agents — used whenever DEMO_MODE=true
(the .env default) and by every scenario test. Never touch a network.

DemoVenueDiscoveryAgent demonstrates tool-level resilience (PlacesTool ->
PlacesFallbackTool) inside a single agent: v3's catalogue has exactly one
agent for web.discover_places, so the "primary fails -> fallback -> success"
scenario is agent-internal here, not agent-selection-level.
"""

import hashlib

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.domain.tools import CalendarEventRequest, RestaurantSearchRequest
from synapse_plane.persistence.repositories import ExternalActionRecordRepository
from synapse_plane.tools.calendar_tool import CalendarReadTool, CalendarWriteTool, choose_slot
from synapse_plane.tools.errors import ToolTimeoutError
from synapse_plane.tools.places_tool import PlacesFallbackTool, PlacesTool

# Canned, hand-written destination facts — the travel use case's demo-mode
# equivalent of PlacesTool's canned restaurants. No network call, ever. This
# is intentionally a small fixed set, not a substitute for real research —
# real mode (Tavily + Gemini) handles any destination genuinely; demo mode
# exists to prove the pipeline shape works with zero live calls.
DESTINATION_FACTS: dict[str, dict[str, object]] = {
    "kandy": {
        "name": "Kandy",
        "highlights": [
            "Temple of the Sacred Tooth Relic",
            "hill-country scenery",
            "cultural shows",
        ],
        "best_for": ["history", "food"],
        "travel_time_hours": 3.0,
        "typical_budget_lkr": 18000,
        "advisory": "Scenic train from Colombo is the recommended route, book ahead on weekends.",
        "top_places": [
            {
                "name": "Temple of the Sacred Tooth Relic",
                "category": "landmark",
                "rating": 4.7,
                "description": "Sri Lanka's most sacred Buddhist shrine, houses a tooth relic.",
            },
            {
                "name": "Kandy Lake",
                "category": "viewpoint",
                "rating": 4.4,
                "description": "A calm lake in the city center, popular for evening walks.",
            },
            {
                "name": "Royal Botanical Gardens, Peradeniya",
                "category": "park",
                "rating": 4.6,
                "description": "One of Asia's largest botanical gardens, a short drive away.",
            },
        ],
    },
    "galle": {
        "name": "Galle",
        "highlights": ["Galle Fort (UNESCO)", "lighthouse", "coastal walks"],
        "best_for": ["history", "hiking"],
        "travel_time_hours": 2.5,
        "typical_budget_lkr": 22000,
        "advisory": "Fort area is walkable; grilled fish is safest for a shellfish allergy.",
        "top_places": [
            {
                "name": "Galle Fort",
                "category": "landmark",
                "rating": 4.7,
                "description": "A 17th-century Dutch fort, UNESCO-listed, with walkable ramparts.",
            },
            {
                "name": "Galle Lighthouse",
                "category": "landmark",
                "rating": 4.3,
                "description": "Sri Lanka's oldest lighthouse, at the fort's southeastern tip.",
            },
            {
                "name": "Jungle Beach",
                "category": "beach",
                "rating": 4.4,
                "description": "A quieter cove beach just outside the fort, good for swimming.",
            },
        ],
    },
    "ella": {
        "name": "Ella",
        "highlights": ["Nine Arches Bridge", "Little Adam's Peak", "Ella Rock hike"],
        "best_for": ["hiking", "history"],
        "travel_time_hours": 6.0,
        "typical_budget_lkr": 20000,
        "advisory": "Take the scenic train from Kandy; book the Ella Rock hike early morning.",
        "top_places": [
            {
                "name": "Nine Arches Bridge",
                "category": "landmark",
                "rating": 4.6,
                "description": "A colonial-era railway viaduct, iconic Sri Lankan photo spot.",
            },
            {
                "name": "Little Adam's Peak",
                "category": "hike",
                "rating": 4.7,
                "description": "A short, accessible sunrise hike with panoramic hill views.",
            },
            {
                "name": "Ella Rock",
                "category": "hike",
                "rating": 4.5,
                "description": "A longer, more challenging trek with the best views in the area.",
            },
        ],
    },
    "sigiriya": {
        "name": "Sigiriya",
        "highlights": ["Sigiriya Rock Fortress (UNESCO)", "frescoes", "Pidurangala viewpoint"],
        "best_for": ["history", "hiking"],
        "travel_time_hours": 4.5,
        "typical_budget_lkr": 19000,
        "advisory": "Climb early morning before the heat; carry water, no shade on the rock.",
        "top_places": [
            {
                "name": "Sigiriya Rock Fortress",
                "category": "landmark",
                "rating": 4.8,
                "description": "A 5th-century rock fortress with ancient frescoes, UNESCO-listed.",
            },
            {
                "name": "Pidurangala Rock",
                "category": "viewpoint",
                "rating": 4.6,
                "description": "A nearby rock climb with the best view of Sigiriya itself.",
            },
        ],
    },
    "mirissa": {
        "name": "Mirissa",
        "highlights": ["whale watching", "Coconut Tree Hill", "beach"],
        "best_for": ["food"],
        "travel_time_hours": 3.0,
        "typical_budget_lkr": 21000,
        "advisory": "Whale watching season is Nov-Apr; grilled fish is a shellfish-safe pick.",
        "top_places": [
            {
                "name": "Coconut Tree Hill",
                "category": "viewpoint",
                "rating": 4.5,
                "description": "A small headland lined with coconut palms overlooking the coast.",
            },
            {
                "name": "Mirissa Beach",
                "category": "beach",
                "rating": 4.4,
                "description": "The main beach, calm water and departure point for whale-watching.",
            },
        ],
    },
    "nuwara_eliya": {
        "name": "Nuwara Eliya",
        "highlights": ["tea plantations", "Horton Plains", "cool climate"],
        "best_for": ["hiking", "history"],
        "travel_time_hours": 5.0,
        "typical_budget_lkr": 20000,
        "advisory": "Bring warm clothes — noticeably colder than the rest of the country.",
        "top_places": [
            {
                "name": "Horton Plains National Park",
                "category": "park",
                "rating": 4.6,
                "description": "A highland plateau hike ending at World's End, a sheer 880m cliff.",
            },
            {
                "name": "Pedro Tea Estate",
                "category": "landmark",
                "rating": 4.3,
                "description": "A working tea plantation and factory offering tours and tastings.",
            },
        ],
    },
}


def _mentioned_destinations(intent: str) -> tuple[list[str], bool]:
    """Returns (destinations, had_canned_data). When the intent names places
    this demo's canned set doesn't cover, that's surfaced honestly — never
    silently substituted with Kandy/Galle as if that answered the question."""
    text = intent.lower().replace(" ", "_")
    found = [name for name in DESTINATION_FACTS if name in text]
    if found:
        return found, True
    return list(DESTINATION_FACTS)[:2], False


# Stand-in for external-browser-use — PlacesTool with PlacesFallbackTool resilience
class DemoVenueDiscoveryAgent(BaseAgent):
    agent_id = "external-browser-use"

    def __init__(self, inject_failure: bool = False):
        self.primary = PlacesTool()
        self.fallback = PlacesFallbackTool()
        self.inject_failure = inject_failure

    def health_check(self) -> bool:
        return True

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if agent_input.required_capability == "web.verify_information":
            return self._verify_information(agent_input)

        request = RestaurantSearchRequest(
            location_label=agent_input.context.get("location", "Colombo")
        )
        tool_calls = []
        try:
            candidates = await self.primary.search(request, inject_failure=self.inject_failure)
            tool_calls.append("places_primary_tool")
        except ToolTimeoutError:
            candidates = await self.fallback.search(request)
            tool_calls.append("places_fallback_tool")

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={"candidates": [c.model_dump(mode="json") for c in candidates]},
            observations=[f"Found {len(candidates)} venues via {tool_calls[-1]}"],
            tool_calls_made=tool_calls,
            confidence=0.85,
        )

    def _verify_information(self, agent_input: AgentInput) -> AgentOutput:
        names, had_data = _mentioned_destinations(agent_input.context.get("intent", ""))
        details = {name: DESTINATION_FACTS[name]["advisory"] for name in names}
        note = (
            None
            if had_data
            else "Demo mode's canned data doesn't cover the place(s) you asked about — "
            f"showing {', '.join(names)} as a stand-in example. Switch to real mode for "
            "genuine research on any destination."
        )
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={
                "details": details,
                "sources": ["demo canned data — no live web call"],
                "demo_data_limitation": note,
            },
            observations=[f"Verified practical details for {', '.join(names)}"],
            tool_calls_made=["canned_destination_facts"],
            confidence=0.85 if had_data else 0.3,
        )


# Stand-in for external-open-deep-research — canned destination comparison data
class DemoResearchAgent(BaseAgent):
    agent_id = "external-open-deep-research"

    def health_check(self) -> bool:
        return True

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        names, had_data = _mentioned_destinations(agent_input.context.get("intent", ""))
        destinations = {name: DESTINATION_FACTS[name] for name in names}
        note = (
            None
            if had_data
            else "Demo mode's canned data doesn't cover the place(s) you asked about — "
            f"showing {', '.join(d['name'] for d in destinations.values())} as a stand-in "
            "example. Switch to real mode for genuine research on any destination."
        )
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={
                "destinations": destinations,
                "summary": f"Researched {' vs '.join(d['name'] for d in destinations.values())}.",
                "demo_data_limitation": note,
            },
            observations=[f"Researched {len(destinations)} destination(s) from canned data"],
            tool_calls_made=["canned_destination_facts"],
            confidence=0.8,
        )


# Stand-in for external-openclaw-personal — mock calendar tools
class DemoCalendarAgent(BaseAgent):
    agent_id = "external-openclaw-personal"

    def __init__(self, action_repo: ExternalActionRecordRepository):
        self.read_tool = CalendarReadTool()
        self.write_tool = CalendarWriteTool(action_repo)

    def health_check(self) -> bool:
        return True

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if agent_input.required_capability == "personal.calendar_create":
            recommendation = agent_input.context.get("recommendation", {})
            availability = agent_input.context.get("availability", {})
            selected = recommendation.get("selected", recommendation)
            request = CalendarEventRequest(
                title=f"Dinner at {selected.get('name', 'Restaurant')}",
                start_time=availability["start_time"],
                end_time=availability["end_time"],
                calendar_id="primary",
                description=f"Arranged via SynapsePlane — {selected.get('address', '')}",
            )
            idempotency_key = f"{agent_input.execution_id}:{agent_input.task_id}:1"
            result = await self.write_tool.create_event(request, idempotency_key)
            return AgentOutput(
                task_id=agent_input.task_id,
                agent_id=self.agent_id,
                success=True,
                result=result.model_dump(mode="json"),
                observations=[f"Created calendar event {result.event_id}"],
                tool_calls_made=["calendar_write_tool"],
                confidence=0.95,
            )

        user_id = agent_input.context.get("user_id", "")
        date = agent_input.context.get("date", "2026-09-10")
        meal = agent_input.context.get("meal", "dinner")
        slots = await self.read_tool.get_availability(user_id, date, meal)
        chosen = choose_slot(slots, agent_input.context.get("preferred_time"))
        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={
                **(chosen.model_dump(mode="json") if chosen else {}),
                "slots": [s.model_dump(mode="json") for s in slots],
            },
            observations=[
                f"Checked {len(slots)} slots for {date}; {sum(1 for s in slots if s.is_free)} free"
            ],
            tool_calls_made=["calendar_read_tool"],
            confidence=0.9,
        )


def _demo_forecast(location: str, target_date: str) -> dict[str, object]:
    # Same hashing approach as FakeEmbeddingService — md5, not the builtin
    # hash(), which PYTHONHASHSEED randomizes per process and would silently
    # break "same input, same forecast" across restarts.
    digest = hashlib.md5(f"{location.lower()}|{target_date}".encode()).hexdigest()
    seed = int(digest[:8], 16) % 100

    rain_chance = seed % 70  # 0-69%, keeps most days rain-unlikely
    rain_likely = rain_chance >= 50
    condition = "rain showers" if rain_likely else ("partly cloudy" if seed % 3 else "clear sky")
    advisory = (
        f"{rain_chance}% chance of rain (demo forecast) — consider indoor seating."
        if rain_likely
        else f"Only {rain_chance}% chance of rain (demo forecast) — outdoor is fine."
    )
    return {
        "available": True,
        "location": location,
        "date": target_date,
        "condition": condition,
        "temperature_c": 24 + (seed % 8),
        "precipitation_probability": rain_chance,
        "rain_likely": rain_likely,
        "advisory": advisory,
    }


# Stand-in for external-weather — deterministic, hash-derived "forecast" so
# the same location+date always gives the same answer, with no network call.
class DemoWeatherAgent(BaseAgent):
    agent_id = "external-weather"

    def health_check(self) -> bool:
        return True

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        target_date = agent_input.context.get("date", "")
        explicit_location = agent_input.context.get("location")

        if explicit_location:
            # Dining case: one specific place, one forecast.
            result = {
                **_demo_forecast(explicit_location, target_date),
                "demo_data_limitation": "Deterministic demo forecast, not a live weather call.",
            }
            observation = f"{explicit_location} on {target_date}: {result['condition']} (demo)"
        else:
            # Travel case: the fixed demo plan has no single literal location
            # to bind, so — like DemoResearchAgent — this reads the candidate
            # destinations straight off the intent text instead.
            names, _ = _mentioned_destinations(agent_input.context.get("intent", ""))
            forecasts = {
                name: _demo_forecast(DESTINATION_FACTS[name]["name"], target_date) for name in names
            }
            result = {
                "forecasts": forecasts,
                "demo_data_limitation": "Deterministic demo forecast, not a live weather call.",
            }
            observation = f"Checked forecast for {', '.join(names)} (demo)"

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result=result,
            observations=[observation],
            tool_calls_made=["demo_forecast_hash"],
            confidence=0.5,
        )
