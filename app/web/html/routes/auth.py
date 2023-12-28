"""auth: Authentication functions for the HTML web app."""
from fastapi import APIRouter, Request, Response
from starlette.templating import _TemplateResponse

from app.datastore.database import DBSession
from app.web import auth, errors
from app.web import field_types as ft
from app.web.auth import OptionalCookieDependency
from app.web.html.const import templates
from app.web.web_models import Token

# ----------- Routers -----------
router = APIRouter(tags=["auth"], prefix="/auth")

ACCESS_TOKEN_KEY = "access_token"  # noqa: S105 (hardcoded-password-string)


@router.post("/token")
async def login_for_access_token(
    response: Response,
    db: DBSession,
    username: ft.StrFormField,
    password: ft.StrFormField,
) -> Token:
    """Authenticate a user, set a cookie with the access token, and return the token."""
    user = auth.authenticate_user(username=username, password=password, db=db)
    token = auth.create_access_token(user=user)
    response.set_cookie(
        key=ACCESS_TOKEN_KEY,
        value=token.access_token,
        httponly=True,
        secure=True,
    )
    return token


REFRESH_ACCESS_PARTIAL = "shared/partials/refresh_access.html"


@router.get("/refresh-token-cookie", response_model=None)
async def refresh_access_token(
    request: Request,
    access_token: OptionalCookieDependency = None,
    remaining_time: int | None = None,
) -> _TemplateResponse:
    """Refresh the access token, if one is already set."""
    if not access_token:
        return templates.TemplateResponse(
            REFRESH_ACCESS_PARTIAL,
            {"request": request, "no_content": True},
        )

    try:
        token = await auth.refresh_token(
            access_token=access_token,
            remaining_time=remaining_time,
        )
    except errors.UserNotValidatedError:
        response = templates.TemplateResponse(
            REFRESH_ACCESS_PARTIAL,
            {"request": request, "no_content": True},
        )
        response.delete_cookie(key=ACCESS_TOKEN_KEY)
        return response
    response = templates.TemplateResponse(
        REFRESH_ACCESS_PARTIAL, {"request": request, "refresh": True}
    )
    response.set_cookie(key=ACCESS_TOKEN_KEY, value=token.access_token)
    return response
