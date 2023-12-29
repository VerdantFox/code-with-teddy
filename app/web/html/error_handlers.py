"""error_handlers: Error handlers for the HTML web package."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from app.web import errors
from app.web.html.flash_messages import FlashCategory, FlashMessage

logger = logging.getLogger(__name__)

ERROR_TEMPLATE = "errors/general_error.html"


def register_error_handlers(app: FastAPI) -> None:
    """Register error handlers for the HTML web package."""

    @app.exception_handler(errors.UserNotValidatedError)
    async def login_expired_in_handler(
        request: Request,
        _error: errors.UserNotValidatedError,
    ) -> RedirectResponse:
        response = RedirectResponse(
            request.url,
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.delete_cookie(key="access_token", httponly=True)
        FlashMessage(
            msg="Login session expired. Please log in again.",
            category=FlashCategory.WARNING,
        ).flash(request)
        return response

    @app.exception_handler(errors.UserNotAuthenticatedError)
    async def not_logged_in_handler(
        request: Request,
        _error: errors.UserNotAuthenticatedError,
    ) -> RedirectResponse:
        FlashMessage(
            msg="Please log in to use that service.",
            category=FlashCategory.ERROR,
        ).flash(request)
        return RedirectResponse(
            request.url_for("html:login_get"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.exception_handler(errors.WebError)
    async def web_error_handler(
        request: Request,
        error: errors.WebError,
    ) -> RedirectResponse:
        return RedirectResponse(
            request.url_for("html:general_error").include_query_params(
                detail=error.detail,
                status_code=error.status_code,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def web_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> RedirectResponse:
        logger.error("Form submission errors: %s", error.errors())
        return RedirectResponse(
            request.url_for("html:general_error").include_query_params(
                detail=(
                    "Something went wrong with the form submission. Please report to Teddy "
                    "if the problem persists."
                ),
                status_code=422,
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.exception_handler(Exception)
    async def general_error(
        request: Request,
        _error: Exception,
    ) -> RedirectResponse:
        return RedirectResponse(
            request.url_for("html:general_error").include_query_params(
                detail=(
                    "Something went wrong on the server."
                    " Contact Teddy Williams to report a problem."
                ),
                status_code=500,
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
