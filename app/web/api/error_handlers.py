"""error_handlers: Error handlers for the API."""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.web.errors import WebError


def register_error_handlers(app: FastAPI) -> None:
    """Register error handlers for the HTML web package."""

    @app.exception_handler(WebError)
    async def web_error_handler(_request: Request, error: WebError) -> JSONResponse:
        """Error handler for all WebErrors to the API."""
        return JSONResponse(
            status_code=error.status_code,
            content=jsonable_encoder({"detail": error.detail}),
        )
