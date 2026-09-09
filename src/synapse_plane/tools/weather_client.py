"""Real weather — Open-Meteo. No API key needed for either endpoint, so this
works in real mode with zero extra setup (unlike Gemini/Tavily/Google
Calendar, which all needed a key or OAuth)."""

from datetime import date as date_type
from typing import Protocol

import httpx

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> short human description (Open-Meteo's own code table)
_WEATHER_CODES: dict[int, str] = {
    0: "clear sky",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    80: "rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


class WeatherForecast:
    def __init__(self, condition: str, temperature_c: float, precipitation_probability: int):
        self.condition = condition
        self.temperature_c = temperature_c
        self.precipitation_probability = precipitation_probability


class WeatherClientProtocol(Protocol):
    async def forecast(self, location: str, target_date: str) -> WeatherForecast: ...


class OpenMeteoWeatherClient:
    async def forecast(self, location: str, target_date: str) -> WeatherForecast:
        async with httpx.AsyncClient(timeout=15) as client:
            geo = await client.get(_GEOCODE_URL, params={"name": location, "count": 1})
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                raise ValueError(f"Could not geocode location: {location}")
            lat, lon = results[0]["latitude"], results[0]["longitude"]

            # Open-Meteo's free daily forecast covers ~16 days ahead; beyond
            # that it silently has no data, so clamp rather than error —
            # this feature degrades to "no forecast that far out", not a crash.
            days_ahead = (date_type.fromisoformat(target_date) - date_type.today()).days
            if days_ahead < 0 or days_ahead > 15:
                raise ValueError(f"{target_date} is outside the 16-day forecast range")

            resp = await client.get(
                _FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weathercode,temperature_2m_max,precipitation_probability_max",
                    "timezone": "auto",
                    "start_date": target_date,
                    "end_date": target_date,
                },
            )
            resp.raise_for_status()
            daily = resp.json()["daily"]
            code = daily["weathercode"][0]
            return WeatherForecast(
                condition=_WEATHER_CODES.get(code, f"code {code}"),
                temperature_c=daily["temperature_2m_max"][0],
                precipitation_probability=daily["precipitation_probability_max"][0],
            )
