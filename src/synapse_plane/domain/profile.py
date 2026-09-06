"""Demo user profile domain models."""

from pydantic import BaseModel, Field


class Location(BaseModel):
    label: str
    latitude: float
    longitude: float


class FoodPreferences(BaseModel):
    cuisines: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    price_level: str = "moderate"
    max_distance_km: float = 10.0
    preferred_dinner_time: str = "19:00"


class TravelPreferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    walking_tolerance: str = "moderate"
    pace: str = "normal"


class CalendarConfig(BaseModel):
    provider: str = "mock"
    calendar_id: str = "primary"


class ApprovalPolicyConfig(BaseModel):
    require_for_external_writes: bool = True
    require_for_financial_actions: bool = True


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
