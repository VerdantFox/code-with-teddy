"""main: FastAPI application instance for the API."""
from fastapi import FastAPI

from app.web.api.routes import auth, users

app = FastAPI()

for route in (auth, users):
    app.include_router(route.router)
