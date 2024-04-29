"""settings: settings management for the app."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the app."""

    # Database settings
    db_connection_string: str
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # JWT settings
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_mins: int = 30

    # App settings
    session_secret: str
    app_name: str = "FastAPI App"
    app_description: str = "FastAPI app"
    app_version: str = "0.1.0"
    app_host: str = ""

    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets", env_file=(".env.dev", ".env"), extra="ignore"
    )


settings: Settings = Settings()


def update_settings(new_settings: Settings) -> None:
    """Update the settings."""
    global settings  # noqa: PLW0603 (global-statement)
    settings = new_settings
