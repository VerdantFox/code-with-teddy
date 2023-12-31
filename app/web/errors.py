"""errors: Web errors."""
from fastapi import status


class WebError(Exception):
    """Base class for all web errors."""

    detail = "Unknown error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str | None = None) -> None:
        if detail:
            self.detail = detail


class UserNotFoundError(WebError):
    """User not found."""

    detail = "User not found"
    status_code = status.HTTP_404_NOT_FOUND


class UserNotAuthenticatedError(WebError):
    """User not authenticated."""

    detail = "Incorrect username or password"
    status_code = status.HTTP_401_UNAUTHORIZED


class UserNotValidatedError(WebError):
    """User not validated."""

    detail = "Unable to validate user from JWT token"
    status_code = status.HTTP_401_UNAUTHORIZED


class UserPermissionsError(WebError):
    """User does not have permission to perform this action."""

    detail = "You do not have permission to perform this action"
    status_code = status.HTTP_403_FORBIDDEN
