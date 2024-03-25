"""main: FastAPI application for HTML frontend."""

import base64
import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.web.html import flash_messages
from app.web.html.const import STATIC_DIR, templates
from app.web.html.error_handlers import register_error_handlers
from app.web.html.routes import auth, blog, errors, landing, users

# TODO: Change this to a secret key and store it in secrets.
SESSION_SECRET = "SUPER-SECRET-KEY"  # noqa: S105 (hardcoded-password-string)

SELF = "'self'"
FONTS_BUNNY = "https://fonts.bunny.net"
UNSAFE_INLINE = "'unsafe-inline'"
UNSAFE_EVAL = "'unsafe-eval'"


class CSPMiddleware(BaseHTTPMiddleware):
    """Add Content-Security-Policy header to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add Content-Security-Policy header to all responses."""
        # Generate a unique nonce
        nonce = base64.b64encode(secrets.token_bytes(16)).decode("utf-8")

        # Add the nonce to the request object
        request.state.nonce = nonce

        response = await call_next(request)
        # HTMX struggles with non-unsafe-inline CSP script
        csp_policy = [
            f"default-src {SELF}",
            f"style-src {SELF}  {FONTS_BUNNY} {UNSAFE_INLINE}",
            f"font-src {SELF} {FONTS_BUNNY}",
            f"script-src {SELF} 'nonce-{nonce}' {UNSAFE_EVAL}",
            "img-src * data:",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_policy)
        return response


app = FastAPI()
app.add_middleware(CSPMiddleware)

routes = (auth, blog, errors, landing, users)
for route in routes:
    app.include_router(route.router)

register_error_handlers(app)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates.env.globals["get_flashed_messages"] = flash_messages.get_flashed_messages
