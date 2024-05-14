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
        # Set sample_rate to 1.0 to capture 100% of errors. (default is 1.0)
        sample_rate=settings.sentry_error_sample_rate,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring. (default is 0.0 )
        traces_sample_rate=settings.sentry_traces_sample_rate,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions. (default is 0.0)
        # We recommend adjusting this value in production.
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        enable_tracing=True,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
