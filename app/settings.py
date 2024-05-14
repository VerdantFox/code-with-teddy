"""settings: settings management for the app."""

import enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, enum.Enum):
    """Environment enum."""

    DEV = "local"
    PROD = "prod"


class Settings(BaseSettings):
    """Settings for the app."""

    # Info settings
    environment: Environment

    # Database settings
    db_connection_string: str
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_create_tables: bool = True

    # JWT settings
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_mins: int = 30

    # App settings
    session_secret: str

    # Email settings
    mailersend_api_key: str
    my_email_address: str = "theodore.f.williams@gmail.com"
    site_email_address: str = "noreply@codewithteddy.dev"

    # Sentry settings
    sentry_dsn: str
    sentry_ingest: str
    sentry_sample_rate: float

    # `.env` overrides `.env.local`
    # `.env.local` is used locally, but is not present in the production docker container
    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets", env_file=(".env.local", ".env"), extra="ignore"
    )


settings: Settings = Settings()


def update_settings(new_settings: Settings) -> None:
    """Update the settings."""
    global settings  # noqa: PLW0603 (global-statement)
    settings = new_settings
