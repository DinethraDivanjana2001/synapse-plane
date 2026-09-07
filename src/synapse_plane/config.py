"""Application configuration, loaded from environment / .env."""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # No default: must come from .env or the environment (docker-compose sets
    # it to the pgvector/pgvector Postgres container). Failing loudly here is
    # deliberate — a silent SQLite fallback would hide a missing pgvector
    # extension until the first embedding write. SQLite is still used
    # directly (bypassing Settings) by tests/integration's isolated fixture.
    database_url: str
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    app_env: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True
    calendar_provider: str = "mock"
    places_provider: str = "mock"
    secret_key: str = "dev-secret"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    context_token_budget: int = 2000       #limt to send LLM
    max_context_items: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        """.env stores CORS_ORIGINS as a plain comma-separated string (see
        .env.example); Pydantic Settings would otherwise require JSON array
        syntax for a list field, which every existing .env in this repo
        predates."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
