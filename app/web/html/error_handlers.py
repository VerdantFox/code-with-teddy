"""error_handlers: Error handlers for the HTML web package."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from app.web import errors
from app.web.html.flash_messages import FlashCategory, FlashMessage

logger = logging.getLogger(__name__)

ERROR_TEMPLATE = "errors/general_error.html"
GENERAL_ERROR_URL_FOR = "html:general_error"


def register_error_handlers(app: FastAPI) -> None:  # noqa: C901 (function too complex)
    """Register error handlers for the HTML web package."""

    @app.exception_handler(errors.UserNotValidatedError)
    async def login_expired_handler(
        request: Request,
        _error: errors.UserNotValidatedError,
    ) -> RedirectResponse:
        """Handle expired login, prompting user re-authentication."""
        response = RedirectResponse(
            request.url,
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.delete_cookie(key="access_token", httponly=True)
        FlashMessage(
            title="Login expired",
            text="Please log in again.",
            category=FlashCategory.WARNING,
        ).flash(request)
        return response

    @app.exception_handler(errors.UserNotAuthenticatedError)
    async def not_logged_in_handler(
        request: Request,
        _error: errors.UserNotAuthenticatedError,
    ) -> RedirectResponse:
        """Redirect unauthenticated users to the login page with a warning."""
        FlashMessage(
            title="Not logged in",
            text="Please log in to use that service.",
            category=FlashCategory.ERROR,
        ).flash(request)
        return RedirectResponse(
            request.url_for("html:login_get").include_query_params(next=request.url),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.exception_handler(errors.WebError)
    async def web_error_handler(
        request: Request,
        error: errors.WebError,
    ) -> RedirectResponse:
        """Handle generic web errors by redirecting to a general error page."""
        return RedirectResponse(
            request.url_for(GENERAL_ERROR_URL_FOR).include_query_params(
                detail=error.detail,
                status_code=error.status_code,
            ),
            status_code=status.HTTP_302_FOUND,
        )

    @app.exception_handler(RequestValidationError)
    async def web_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> RedirectResponse:
        """Log form validation errors and redirect to a general error page."""
        logger.error("Form submission errors: %s", error.errors())
        return RedirectResponse(
            request.url_for(GENERAL_ERROR_URL_FOR).include_query_params(
                detail=(
                    "Something went wrong with the form submission. Please report to Teddy "
                    "if the problem persists."
                ),
                status_code=422,
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.exception_handler(errors.PasswordResetTokenExpiredError)
    async def password_reset_expired_handler(
        request: Request,
        _error: errors.UserNotValidatedError,
    ) -> RedirectResponse:
        """Handle expired password reset token."""
        FlashMessage(
            title="Password reset token expired",
            text="Please request a new password reset email.",
            category=FlashCategory.WARNING,
        ).flash(request)
        return RedirectResponse(request.url_for("html:get_request_password_reset"))

    @app.exception_handler(errors.PasswordResetTokenNotFoundError)
    async def password_reset_not_found_handler(
        request: Request,
        _error: errors.UserNotValidatedError,
    ) -> RedirectResponse:
        """Handle not found password reset token."""
        FlashMessage(
            title="Password reset token not found",
            text="Please request a new password reset email.",
            category=FlashCategory.WARNING,
        ).flash(request)
        return RedirectResponse(request.url_for("html:get_request_password_reset"))

    @app.exception_handler(Exception)
    async def general_error(
        request: Request,
        _error: Exception,
    ) -> RedirectResponse:
        """Handle unexpected server errors by redirecting to a general error page."""
        return RedirectResponse(
            request.url_for(GENERAL_ERROR_URL_FOR).include_query_params(
                detail=(
                    "Something went wrong on the server."
                    " Contact Teddy Williams to report a problem."
                ),
                status_code=500,
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.exception_handler(404)
    async def not_found_error(
        request: Request,
        _error: Exception,
    ) -> RedirectResponse:
        """Redirect to a general error page for 404 Not Found errors."""
        return RedirectResponse(
            request.url_for(GENERAL_ERROR_URL_FOR).include_query_params(
                detail="Page not found.",
                status_code=404,
            ),
            status_code=status.HTTP_302_FOUND,
        )
