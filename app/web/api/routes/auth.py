"""auth: Authentication routes for the API."""
from fastapi import APIRouter

from app.datastore.database import DBSession
from app.web import auth, web_models
from app.web import field_types as ft

# ----------- Routers -----------
router = APIRouter(tags=["auth"], prefix="/auth")


@router.post("/token")
async def login_for_access_token(
    db: DBSession,
    username_or_email: ft.StrFormField,
    password: ft.StrFormField,
) -> web_models.Token:
    """Authenticate the user and return an access token."""
    user = auth.authenticate_user(username_or_email=username_or_email, password=password, db=db)
    return auth.create_access_token(user=user)
