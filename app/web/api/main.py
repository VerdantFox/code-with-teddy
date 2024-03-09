"""main: FastAPI application instance for the API."""

from fastapi import FastAPI

from app.web.api.error_handlers import register_error_handlers
from app.web.api.routes import auth, users

app = FastAPI()

for route in (auth, users):
    app.include_router(route.router)

register_error_handlers(app)
