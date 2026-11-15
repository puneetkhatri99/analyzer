"""Settings, read from environment variables. In local development server/.env fills in any that aren't set."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVER_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = None
    # Only needed if a dashboard on another address calls the API. The built-in dashboard shares its address.
    allowed_origin: str = "*"

    # Admin panel: AI extraction of jobs from any URL.
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"

    # Logs also go to Axiom when a token is set (app/core/logs.py).
    axiom_token: str | None = None
    axiom_dataset: str = "analyzer"

    # push-data: the hosted database's direct (non-pooler) connection string.
    neon_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
