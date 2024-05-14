"""monitoring: monitoring, error tracking, metrics, logging, and alerting."""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.settings import settings


def initialize_sentry() -> None:
    """Initialize Sentry for error tracking."""
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment.value,
        sample_rate=settings.sentry_sample_rate,
        enable_tracing=True,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
    )
