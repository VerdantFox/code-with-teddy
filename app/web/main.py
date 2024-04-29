"""main: FastAPI application for the web app.

This is the main entrypoint for the web app. It mounts the API and HTML apps.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sqlalchemy
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.datastore import db_models
from app.datastore.database import get_engine
from app.settings import settings
from app.web.api import main as api_main
from app.web.html import main as html_main


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001 (unused-argument)
    """Code to run before taking any requests and just before shutdown."""
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(db_models.Base.metadata.create_all)
    except sqlalchemy.exc.OperationalError as e:  # pragma: no cover
        err_msg = (
            "Could not connect to the database. Check the connection string."
            " Is the server running on that host and accepting TCP/IP connections?"
        )
        raise RuntimeError(err_msg) from e
    yield
    # Code to run before shutdown.
    await engine.dispose()


def create_app() -> FastAPI:
    """Create the FastAPI app."""
    app = FastAPI(lifespan=lifespan)

    origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "http://192.168.1.12",
        "http://192.168.1.12:8000",
        "http://192.168.1.12:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

    @app.get("/api")
    async def api_home(request: Request) -> RedirectResponse:
        """Redirect the main API route to the Swagger UI."""
        return RedirectResponse(url=request.url_for("api:swagger_ui_html"), status_code=302)

    app.mount("/api/v1", api_main.app, name="api")
    app.mount("/", html_main.app, name="html")

    return app
