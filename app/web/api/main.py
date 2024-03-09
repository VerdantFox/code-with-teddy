"""main: FastAPI application instance for the API."""

import importlib

from fastapi import FastAPI

from app.web.api.routes import auth, users

app = FastAPI()

for route in (auth, users):
    app.include_router(route.router)

# Import error handlers after app is defined
# Can't use standard import name because `app` above conflicts with
# the `app` package
importlib.import_module("app.web.api.error_handlers")
