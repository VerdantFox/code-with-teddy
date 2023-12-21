"""main: FastAPI application for HTML frontend."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.html import flash_messages
from app.web.html.const import STATIC_DIR, templates
from app.web.html.error_handlers import register_error_handlers
from app.web.html.routes import auth, blog, errors, landing, users

# TODO: Change this to a secret key and store it in secrets.
SESSION_SECRET = "SUPER-SECRET-KEY"  # noqa: S105 (hardcoded-password-string)

app = FastAPI()

routes = (auth, blog, errors, landing, users)
for route in routes:
    app.include_router(route.router)

register_error_handlers(app)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates.env.globals["get_flashed_messages"] = flash_messages.get_flashed_messages
