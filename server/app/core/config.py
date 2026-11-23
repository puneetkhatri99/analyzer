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

    # "production" on Render (render.yaml). With an Axiom token there, logs go to Axiom only, not to files.
    app_env: str = "local"

    # Outgoing email (app/shared/email.py, EMAIL.md): any SMTP server. ALERT_FROM_EMAIL must be an address the server
    # may send from, e.g. "MinistryHub Leads <alerts@ministryhub.org>". SITE_URL links the emails to the admin.
    # Port 465 = SSL, any other (587) = STARTTLS. resend_api_key is the older setting, used only if SMTP_HOST is empty.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    resend_api_key: str | None = None
    alert_from_email: str | None = None
    site_url: str = "http://localhost:5173"

    # The weekly newsletter sync (app/leads/crm_sync.py). Off until both are set. The key ends in its data centre
    # ("…-us21"); the list ID is the audience's ID (Mailchimp: Audience → Settings → Audience name and defaults).
    mailchimp_api_key: str | None = None
    mailchimp_list_id: str | None = None

    # Sign-ups from these email domains (the team testing the site) aren't stored as leads. Comma-separated.
    ignored_lead_domains: str = "ministryhub.org"

    # The daily feed job (app/ingestion/daily_feed.py). The feed link is saved by an admin in Admin → Settings;
    # FEED_URL is only the fallback. FEED_HOUR_UTC: the job runs once a day after this hour.
    # ENRICH_MAX_PER_RUN: churches the AI searches the web for per run (each search costs about a cent).
    feed_url: str | None = None
    feed_hour_utc: int = 6
    enrich_max_per_run: int = 50

    # Overrides the default log level (API: INFO, scripts: DEBUG), e.g. LOG_LEVEL=DEBUG to look into a problem.
    log_level: str | None = None

    # Logs also go to Axiom when a token is set (app/core/logs.py).
    axiom_token: str | None = None
    axiom_dataset: str = "analyzer"

    # push-data: the hosted database's direct (non-pooler) connection string.
    neon_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
