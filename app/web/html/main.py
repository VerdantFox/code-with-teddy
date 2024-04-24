"""main: FastAPI application for HTML frontend."""

import base64
import importlib
import pkgutil
import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Have to import 'jinja_globals' to register the jinja globals in this module
from app.web.html import jinja_globals, routes  # noqa: F401 (import-unused)
from app.web.html.const import STATIC_DIR
from app.web.html.error_handlers import register_error_handlers

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
            "frame-src youtube.com www.youtube.com scratch.mit.edu",
            f"style-src {SELF}  {FONTS_BUNNY} {UNSAFE_INLINE}",
            f"font-src {SELF} {FONTS_BUNNY}",
            f"script-src {SELF} 'nonce-{nonce}' {UNSAFE_EVAL}",
            "img-src * data:",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_policy)
        return response


app = FastAPI()
app.add_middleware(CSPMiddleware)


modules = [name for _, name, _ in pkgutil.iter_modules(routes.__path__)]
route_modules = tuple(importlib.import_module(f"app.web.html.routes.{name}") for name in modules)
for route_module in route_modules:
    app.include_router(route_module.router)

register_error_handlers(app)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
