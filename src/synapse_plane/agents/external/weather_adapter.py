"""Weather check — usable by both the dining and travel use cases: an
outdoor-seating dinner or a hiking trip both care whether it's going to rain.
Real Open-Meteo call, no API key required.
"""

from synapse_plane.agents.base import AgentInput, AgentOutput, BaseAgent
from synapse_plane.agents.errors import AgentUnavailableError
from synapse_plane.tools.weather_client import WeatherClientProtocol

_RAIN_THRESHOLD_PCT = 50


class WeatherAdapter(BaseAgent):
    agent_id = "external-weather"

    def __init__(self, weather_client: WeatherClientProtocol | None = None):
        self.weather_client = weather_client

    def health_check(self) -> bool:
        return self.weather_client is not None

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        if not self.health_check():
            raise AgentUnavailableError(self.agent_id, "weather client not configured")

        location = agent_input.context.get("location") or agent_input.context.get(
            "home_location", "Colombo"
        )
        target_date = agent_input.context.get("date", "")

        try:
            forecast = await self.weather_client.forecast(location, target_date)  # type: ignore[union-attr]
        except ValueError as exc:
            # Out of forecast range or unknown place — a soft "no data"
            # result, not a task failure; nothing downstream depends on it.
            return AgentOutput(
                task_id=agent_input.task_id,
                agent_id=self.agent_id,
                success=True,
                result={"available": False, "reason": str(exc)},
                observations=[f"No forecast available for {location} on {target_date}"],
                tool_calls_made=["open_meteo"],
                confidence=0.2,
            )

        rain_likely = forecast.precipitation_probability >= _RAIN_THRESHOLD_PCT
        advisory = (
            f"{forecast.precipitation_probability}% chance of rain — consider indoor seating."
            if rain_likely
            else f"Only {forecast.precipitation_probability}% chance of rain — outdoor is fine."
        )

        return AgentOutput(
            task_id=agent_input.task_id,
            agent_id=self.agent_id,
            success=True,
            result={
                "available": True,
                "location": location,
                "date": target_date,
                "condition": forecast.condition,
                "temperature_c": forecast.temperature_c,
                "precipitation_probability": forecast.precipitation_probability,
                "rain_likely": rain_likely,
                "advisory": advisory,
            },
            observations=[f"{location} on {target_date}: {forecast.condition}"],
            tool_calls_made=["open_meteo"],
            confidence=0.9,
        )
