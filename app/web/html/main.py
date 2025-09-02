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

from app.settings import settings

# Have to import 'jinja_globals' to register the jinja globals in this module
from app.web.html import jinja_globals, routes  # noqa: F401 (import-unused)
from app.web.html.const import STATIC_DIR
from app.web.html.error_handlers import register_error_handlers

SELF = "'self'"
YOUTUBE = "youtube.com www.youtube.com"
SCRATCH = "scratch.mit.edu"
FONTS_BUNNY = "https://fonts.bunny.net"
UNSAFE_INLINE = "'unsafe-inline'"
UNSAFE_EVAL = "'unsafe-eval'"
SENTRY_JS_CDN = "https://js.sentry-cdn.com"
SENTRY_BROWSER_CDN = "https://browser.sentry-cdn.com"
SENTRY_INGEST = settings.sentry_ingest
BLOB = "blob:"
DATA = "data:"


class CSPMiddleware(BaseHTTPMiddleware):
    """Add Content-Security-Policy header to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add Content-Security-Policy header to all responses."""
        # Generate a unique nonce for this request
        nonce = base64.b64encode(secrets.token_bytes(16)).decode("utf-8")

        # Add the nonce to the request object so templates can access it
        request.state.nonce = nonce

        response = await call_next(request)

        # Build comprehensive CSP policy with nonce
        # HTMX and some inline scripts require 'unsafe-inline' as fallback
        csp_policy = [
            f"default-src {SELF}",
            (
                f"script-src {SELF} 'nonce-{nonce}' {UNSAFE_EVAL} {UNSAFE_INLINE} "
                f"{SENTRY_JS_CDN} {SENTRY_BROWSER_CDN}"
            ),
            f"style-src {SELF} {FONTS_BUNNY} {UNSAFE_INLINE}",
            f"font-src {SELF} {FONTS_BUNNY}",
            f"frame-src {YOUTUBE} {SCRATCH}",
            f"connect-src {SELF} {SENTRY_INGEST}",
            f"worker-src {SELF} {SENTRY_JS_CDN} {SENTRY_BROWSER_CDN} {BLOB}",
            f"img-src * {DATA} {BLOB}",
            f"media-src {SELF} {DATA} {BLOB}",
            "object-src 'none'",
            f"base-uri {SELF}",
            f"form-action {SELF}",
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
