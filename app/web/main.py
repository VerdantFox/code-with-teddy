"""main: FastAPI application for the web app.

This is the main entrypoint for the web app. It mounts the API and HTML apps.
"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.datastore import db_models
from app.datastore.database import engine
from app.web.api import main as api_main
from app.web.html import main as html_main

# TODO: Change this to a secret key and store it in secrets.
SESSION_SECRET = "SUPER-SECRET-KEY"  # noqa: S105 (hardcoded-password-string)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

db_models.Base.metadata.create_all(bind=engine)


@app.get("/api")
async def api_home(request: Request) -> RedirectResponse:
    """Redirect the main API route to the Swagger UI."""
    return RedirectResponse(url=request.url_for("api:swagger_ui_html"), status_code=302)


app.mount("/api", api_main.app, name="api")
app.mount("/", html_main.app, name="html")
