"""Application configuration, loaded from environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./synapse_plane_dev.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    app_env: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True
    calendar_provider: str = "mock"
    places_provider: str = "mock"
    secret_key: str = "dev-secret"
    cors_origins: list[str] = ["http://localhost:3000"]
    context_token_budget: int = 2000
    max_context_items: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
