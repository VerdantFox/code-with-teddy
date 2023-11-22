"""users: HTML routes for users."""
from typing import Annotated

import sqlalchemy
from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import _TemplateResponse
from wtforms import Form, PasswordField, StringField, validators

from app.datastore import db_models
from app.datastore.database import DBSession
from app.permissions import Role
from app.web import auth, errors
from app.web.html.const import templates
from app.web.html.flash_messages import FlashCategory, FlashMessage
from app.web.html.routes.auth import login_for_access_token

# ----------- Routers -----------
router = APIRouter(tags=["users"], prefix="/users")

LOGIN_TEMPLATE = "users/login.html"
REGISTER_TEMPLATE = "users/register.html"


class LoginForm(Form):
    """Form for user login page."""

    username: StringField = StringField(
        "Username",
        validators=[validators.Length(min=3, max=25)],
    )
    password: PasswordField = PasswordField(
        "Password",
        validators=[validators.Length(min=8, max=25)],
    )


@router.get("/login", response_class=HTMLResponse)
async def login_get(
    request: Request,
    username: Annotated[str | None, Query()] = None,
) -> _TemplateResponse:
    """Return the login page for GET requests."""
    login_form = LoginForm()
    if username:
        login_form.username.data = username
    headers = {
        "HX-Replace-Url": str(request.url_for("html:login_get")),
        "HX-Refresh": "true",
    }
    return templates.TemplateResponse(
        LOGIN_TEMPLATE,
        {"request": request, "form": login_form},
        headers=headers,
    )


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    db: DBSession,
) -> _TemplateResponse | RedirectResponse:
    """Log the user in and redirect to the home page."""
    form_data = await request.form()
    login_form = LoginForm(**form_data)
    if not login_form.validate():
        return templates.TemplateResponse(
            LOGIN_TEMPLATE,
            {
                "request": request,
                "message": FlashMessage(
                    msg="Invalid username or password",
                    category=FlashCategory.ERROR,
                ),
                "form": login_form,
            },
        )
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    try:
        await login_for_access_token(
            response=response,
            db=db,
            username=login_form.username.data,
            password=login_form.password.data,
        )
    except errors.UserNotAuthenticatedError as e:
        return templates.TemplateResponse(
            LOGIN_TEMPLATE,
            {
                "request": request,
                "message": FlashMessage(msg=e.detail, category=FlashCategory.ERROR),
                "form": login_form,
            },
        )

    FlashMessage(
        msg="You are logged in!",
        category=FlashCategory.SUCCESS,
        timeout=5,
    ).flash(request)
    return response


class RegisterUserForm(Form):
    """Form for user registration page."""

    email: StringField = StringField(
        "Email",
        validators=[validators.Length(min=1, max=25)],
    )
    username: StringField = StringField(
        "Username",
        validators=[validators.Length(min=3, max=25)],
    )
    first_name: StringField = StringField(
        "First Name",
        validators=[validators.Length(min=1, max=25)],
    )
    last_name: StringField = StringField(
        "Last Name",
        validators=[validators.Length(min=1, max=25)],
    )
    password: PasswordField = PasswordField(
        "Password",
        validators=[validators.Length(min=8, max=25)],
    )
    confirm_password: PasswordField = PasswordField(
        "Confirm Password",
        validators=[
            validators.Length(min=8, max=25),
            validators.EqualTo("password", message="Passwords must match"),
        ],
    )


@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request) -> _TemplateResponse:
    """Return the user registration page."""
    form_data = await request.form()
    login_form = RegisterUserForm(**form_data)
    return templates.TemplateResponse(
        REGISTER_TEMPLATE,
        {"request": request, "form": login_form},
    )


@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    db: DBSession,
) -> _TemplateResponse | RedirectResponse:
    """Register a new user."""
    form_data = await request.form()
    register_form = RegisterUserForm(**form_data)
    if not register_form.validate():
        return templates.TemplateResponse(
            REGISTER_TEMPLATE,
            {
                "request": request,
                "message": FlashMessage(
                    msg="Invalid form fields.",
                    category=FlashCategory.ERROR,
                ),
                "form": register_form,
            },
        )
    user_model = db_models.User(
        email=register_form.email.data,
        username=register_form.username.data,
        first_name=register_form.first_name.data,
        last_name=register_form.last_name.data,
        hashed_password=auth.hash_password(register_form.password.data),
        role=Role.USER,
        is_active=True,
    )
    db.add(user_model)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        return templates.TemplateResponse(
            REGISTER_TEMPLATE,
            {
                "request": request,
                "message": FlashMessage(
                    msg="Username or email already exists. Already have an account? Login!",
                    category=FlashCategory.ERROR,
                ),
                "form": register_form,
            },
        )
    db.refresh(user_model)
    FlashMessage(
        msg=f"User {user_model.username} created!",
        category=FlashCategory.SUCCESS,
        timeout=5,
    ).flash(request)
    return RedirectResponse(
        request.url_for("html:login_get").include_query_params(
            username=user_model.username,
        ),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/logout", response_class=HTMLResponse)
async def logout(request: Request) -> RedirectResponse:
    """Log the user out and redirect to the home page."""
    response = RedirectResponse(
        request.url_for("html:login_get"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(key="access_token", httponly=True)
    FlashMessage(
        msg="You are logged out!",
        category=FlashCategory.SUCCESS,
        timeout=5,
    ).flash(request)
    return response
