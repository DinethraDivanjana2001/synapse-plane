"""Demo user profile domain models."""

from pydantic import BaseModel, Field


# A named point on the map
class Location(BaseModel):
    label: str
    latitude: float
    longitude: float


# Dining preferences used to rank restaurant candidates
class FoodPreferences(BaseModel):
    cuisines: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    price_level: str = "moderate"
    max_distance_km: float = 10.0
    preferred_dinner_time: str = "19:00"


# Travel-planning preferences for the trip-research use case
class TravelPreferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    walking_tolerance: str = "moderate"
    pace: str = "normal"


# Which calendar provider/account this user's events go to
class CalendarConfig(BaseModel):
    provider: str = "mock"
    calendar_id: str = "primary"


# Which action categories require human approval
class ApprovalPolicyConfig(BaseModel):
    require_for_external_writes: bool = True
    require_for_financial_actions: bool = True


# The demo user's full profile
class UserProfile(BaseModel):
    user_id: str
    display_name: str
    home_location: Location
    timezone: str
    language: str = "en"
    currency: str = "LKR"
    food_preferences: FoodPreferences
    travel_preferences: TravelPreferences
    calendar: CalendarConfig
    approval_policy: ApprovalPolicyConfig
