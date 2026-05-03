"""error_handlers: Error handlers for the HTML web package."""

import logging
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from app import errors
from app.web.html.flash_messages import FlashCategory, FlashMessage

logger = logging.getLogger(__name__)

ERROR_TEMPLATE = "errors/general_error.html"
GENERAL_ERROR_URL_FOR = "html:general_error"


async def login_expired_handler(
    request: Request,
    _error: Exception,
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


async def not_logged_in_handler(
    request: Request,
    _error: Exception,
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


async def web_error_handler(
    request: Request,
    error: Exception,
) -> RedirectResponse:
    """Handle generic web errors by redirecting to a general error page."""
    app_error = cast(errors.AppError, error)
    return RedirectResponse(
        request.url_for(GENERAL_ERROR_URL_FOR).include_query_params(
            detail=app_error.detail,
            status_code=app_error.status_code,
        ),
        status_code=status.HTTP_302_FOUND,
    )


async def web_validation_error(
    request: Request,
    error: Exception,
) -> RedirectResponse:
    """Log form validation errors and redirect to a general error page."""
    logger.error("Form submission errors: %s", cast(RequestValidationError, error).errors())
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


async def password_reset_expired_handler(
    request: Request,
    _error: Exception,
) -> RedirectResponse:
    """Handle expired password reset token."""
    FlashMessage(
        title="Password reset token expired",
        text="Please request a new password reset email.",
        category=FlashCategory.WARNING,
    ).flash(request)
    return RedirectResponse(request.url_for("html:get_request_password_reset"), status_code=303)


async def password_reset_not_found_handler(
    request: Request,
    _error: Exception,
) -> RedirectResponse:
    """Handle not found password reset token."""
    FlashMessage(
        title="Password reset token not found",
        text="Please request a new password reset email.",
        category=FlashCategory.WARNING,
    ).flash(request)
    return RedirectResponse(request.url_for("html:get_request_password_reset"), status_code=303)


async def general_error(
    request: Request,
    _error: Exception,
) -> RedirectResponse:
    """Handle unexpected server errors by redirecting to a general error page."""
    return RedirectResponse(
        request.url_for(GENERAL_ERROR_URL_FOR).include_query_params(
            detail=(
                "Something went wrong on the server. Contact Teddy Williams to report a problem."
            ),
            status_code=500,
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )


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


def register_error_handlers(app: FastAPI) -> None:
    """Register error handlers for the HTML web package."""
    app.add_exception_handler(errors.UserNotValidatedError, login_expired_handler)
    app.add_exception_handler(errors.UserNotAuthenticatedError, not_logged_in_handler)
    app.add_exception_handler(errors.AppError, web_error_handler)
    app.add_exception_handler(RequestValidationError, web_validation_error)
    app.add_exception_handler(errors.PasswordResetTokenExpiredError, password_reset_expired_handler)
    app.add_exception_handler(
        errors.PasswordResetTokenNotFoundError, password_reset_not_found_handler
    )
    app.add_exception_handler(Exception, general_error)
    app.add_exception_handler(404, not_found_error)
