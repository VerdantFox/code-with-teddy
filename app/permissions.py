"""permissions: Permissions for the app."""
from enum import Enum


class Role(str, Enum):
    """User roles."""

    UNAUTHENTICATED = "unauthenticated"
    USER = "user"
    REVIEWER = "reviewer"
    ADMIN = "admin"
