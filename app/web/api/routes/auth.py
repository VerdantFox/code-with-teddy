"""auth: Authentication routes for the API."""

from typing import Annotated

from fastapi import APIRouter, Form

from app.datastore.database import DBSession
from app.web import auth, web_models
from app.web import field_types as ft

# ----------- Routers -----------
router = APIRouter(tags=["auth"], prefix="/auth")


@router.post("/token")
async def login_for_access_token(
    db: DBSession,
    username: Annotated[str, Form(description="Username or email")],
    password: ft.StrFormField,
) -> web_models.Token:
    """Authenticate the user and return an access token."""
    # NOTE: Have to use `username` for authentication variable name
    #    to work with FastAPI's swagger authentication, even if
    #    email is allowed.
    username_or_email = username
    user = await auth.authenticate_user(
        username_or_email=username_or_email, password=password, db=db
    )
    return auth.create_access_token(user=user)
