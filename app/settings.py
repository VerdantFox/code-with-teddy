"""settings: settings management for the app."""

import enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, enum.Enum):
    """Enum for environment types."""

    LOCAL = "local"
    DOCKER = "docker"
    PROD = "prod"

    def __str__(self) -> str:
        return self.value


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
    encryption_key: str

    # Email settings
    mailersend_api_key: str
    my_email_address: str = "theodore.f.williams@gmail.com"
    site_email_address: str = "noreply@codewithteddy.dev"

    # Sentry settings
    sentry_dsn: str
    sentry_ingest: str
    sentry_cdn: str
    sentry_error_sample_rate: float  # <-- percentage of errors sampled
    sentry_traces_sample_rate: float  # <-- percentage of traces sampled
    sentry_profiles_sample_rate: float  # <-- percentage of traces profiled
    #     (relative to sentry_traces_sample_rate)
    # NOTE: Sentry client session sample rate currently fixed value, but could be added here

    # `.env` overrides `.env.local`
    # `.env.local` is used locally, but is not present in the production docker container
    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets", env_file=(".env.local", ".env"), extra="ignore"
    )

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        match self.environment:
            case Environment.LOCAL:
                return "http://localhost:8000"
            case Environment.DOCKER:
                return "http://localhost"
            case Environment.PROD:
                return "https://codewithteddy.dev"
            case _:
                error_msg = "Invalid environment"
                raise ValueError(error_msg)


settings: Settings = Settings()  # ty: ignore[missing-argument]  (missing params come from `.env` or `.env.local`)


def update_settings(new_settings: Settings) -> None:
    """Update the settings."""
    global settings  # noqa: PLW0603 (global-statement)
    settings = new_settings
