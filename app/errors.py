"""errors: Domain exceptions for the app.

These are intentionally HTTP-agnostic at the class level so that the service
layer does not depend on the web layer.  The `status_code` attributes are
defined here as a convenience — they are read by the web error-handlers but
carry no runtime coupling to FastAPI/Starlette.
"""

from fastapi import status


class AppError(Exception):
    """Base class for all application errors."""

    detail = "Unknown error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str | None = None) -> None:
        if detail:
            self.detail = detail


class UserNotFoundError(AppError):
    """User not found."""

    detail = "User not found"
    status_code = status.HTTP_404_NOT_FOUND


class BlogPostNotFoundError(AppError):
    """Blog post not found."""

    detail = "Blog post not found"
    status_code = status.HTTP_404_NOT_FOUND


class BlogPostCommentNotFoundError(AppError):
    """Blog post comment not found."""

    detail = "Blog post comment not found"
    status_code = status.HTTP_404_NOT_FOUND


class BlogPostMediaNotFoundError(AppError):
    """Blog post media not found."""

    detail = "Blog post media not found"
    status_code = status.HTTP_404_NOT_FOUND


class BlogPostSeriesNotFoundError(AppError):
    """Blog post series not found."""

    detail = "Blog post series not found"
    status_code = status.HTTP_404_NOT_FOUND


class PasswordResetTokenNotFoundError(AppError):
    """Password reset token not found."""

    detail = "Password reset token not found"
    status_code = status.HTTP_404_NOT_FOUND


class PasswordResetTokenExpiredError(AppError):
    """Password reset token expired."""

    detail = "Password reset token expired"
    status_code = status.HTTP_400_BAD_REQUEST


class UserNotAuthenticatedError(AppError):
    """User not authenticated."""

    detail = "Incorrect username or password"
    status_code = status.HTTP_401_UNAUTHORIZED


class UserNotValidatedError(AppError):
    """User not validated."""

    detail = "Unable to validate user from JWT token"
    status_code = status.HTTP_401_UNAUTHORIZED


class UserPermissionsError(AppError):
    """User does not have permission to perform this action."""

    detail = "You do not have permission to perform this action"
    status_code = status.HTTP_403_FORBIDDEN


class UserAlreadyExistsError(AppError):
    """User already exists."""

    detail = "User already exists"
    status_code = status.HTTP_409_CONFLICT
