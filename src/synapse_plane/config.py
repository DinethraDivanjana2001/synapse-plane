"""Application configuration, loaded from environment / .env."""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


# App-wide config, loaded from environment / .env
class Settings(BaseSettings):
    database_url: str  # required, no default — must come from .env/environment
    openai_api_key: str = ""  # holds the Gemini key here — see llm/gemini_client.py
    openai_model: str = "gpt-4o-mini"  # set to a Gemini model name in .env
    tavily_api_key: str = ""
    google_calendar_credentials_path: str = "credentials.json"
    google_calendar_token_path: str = "token.json"
    # gemini-embedding-001, via the same OpenAI-compatible endpoint as chat —
    # verified against a real call (3072-dim output). No separate account
    # needed, unlike the originally-planned OpenAI text-embedding-3-small.
    embedding_model: str = "gemini-embedding-001"
    app_env: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True
    calendar_provider: str = "mock"  # "mock" | "google"
    places_provider: str = "mock"
    secret_key: str = "dev-secret"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    context_token_budget: int = 2000
    max_context_items: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        """Parse CORS_ORIGINS as comma-separated, not JSON."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
