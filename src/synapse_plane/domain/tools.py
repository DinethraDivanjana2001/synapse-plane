"""I/O schemas for deterministic tool calls (restaurant search, calendar)."""

from datetime import datetime

from pydantic import BaseModel, Field


# A restaurant search request
class RestaurantSearchRequest(BaseModel):
    location_label: str
    cuisines: list[str] = Field(default_factory=list)
    max_distance_km: float = 10.0
    price_level: str = "moderate"


# One candidate restaurant returned by a places tool
class RestaurantCandidate(BaseModel):
    name: str
    cuisine: str
    rating: float
    price_level: str
    is_quiet: bool
    distance_km: float
    source: str


# A free/busy window on the calendar
class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_free: bool


# A request to create a calendar event
class CalendarEventRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    calendar_id: str
    description: str = ""


# The result of creating (or replaying) a calendar event
class CalendarEventResult(BaseModel):
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    calendar_id: str
