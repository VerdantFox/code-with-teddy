"""users: HTML routes for users."""
import re
from typing import Annotated
from uuid import uuid4

import sqlalchemy
from fastapi import APIRouter, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from starlette.templating import _TemplateResponse
from wtforms import (
    FileField,
    Form,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    validators,
)

from app import constants
from app.datastore import db_models
from app.datastore.database import DBSession
from app.permissions import Role
from app.services.media import media_handler
from app.web import auth, errors
from app.web.html.const import templates
from app.web.html.flash_messages import FlashCategory, FlashMessage, FormErrorMessage
from app.web.html.routes.auth import login_for_access_token

# ----------- Routers -----------
router = APIRouter(tags=["users"])

LOGIN_TEMPLATE = "users/login.html"
REGISTER_TEMPLATE = "users/register.html"


class LoginForm(Form):
    """Form for user login page."""

    username_or_email: StringField = StringField(
        "Username or Email",
        description="awesome@email.com",
        validators=[validators.Length(min=3, max=25)],
    )
    password: PasswordField = PasswordField(
        "Password",
        validators=[validators.Length(min=8, max=25)],
    )
    redirect_url: HiddenField = HiddenField()


@router.get("/login", response_model=None)
async def login_get(
    request: Request,
    username: Annotated[str | None, Query()] = None,
    redirect_url: Annotated[str | None, Query(alias="next")] = None,
) -> _TemplateResponse:
    """Return the login page for GET requests."""
    login_form = LoginForm()
    if username:
        login_form.username_or_email.data = username
    if redirect_url:
        login_form.redirect_url.data = redirect_url
    return templates.TemplateResponse(
        LOGIN_TEMPLATE,
        {constants.REQUEST: request, "login_form": login_form},
    )


@router.post("/login", response_model=None)
async def login_post(
    request: Request,
    db: DBSession,
) -> _TemplateResponse | RedirectResponse:
    """Log the user in and redirect to the home page."""
    form_data = await request.form()
    login_form = LoginForm(**form_data)
    if not login_form.validate():
        return templates.TemplateResponse(
            "users/partials/login_form.html",
            {
                constants.REQUEST: request,
                "message": FormErrorMessage(),
                "login_form": login_form,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    redirect_url = login_form.redirect_url.data or "/"

    # Why not a RedirectResponse?
    # Because we need to set the HX-Redirect header to perform
    # a full-page redirect to update the url and title.
    # HTML redirects don't pass through headers so HTMX
    # can't see the redirect.
    response = templates.TemplateResponse(
        "users/partials/login_form.html",
        {
            constants.REQUEST: request,
            "login_form": login_form,
        },
        headers={"HX-Redirect": redirect_url},
    )
    try:
        await login_for_access_token(
            response=response,
            db=db,
            username_or_email=login_form.username_or_email.data,
            password=login_form.password.data,
        )
    except errors.UserNotAuthenticatedError as e:
        return templates.TemplateResponse(
            "users/partials/login_form.html",
            {
                constants.REQUEST: request,
                "message": FormErrorMessage(msg=e.detail),
                "login_form": login_form,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    FlashMessage(
        msg="You are logged in!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return response


class RegisterUserForm(Form):
    """Form for user registration page."""

    email: StringField = StringField(
        "Email",
        description="awesome@email.com",
        validators=[validators.Length(min=1, max=25)],
    )
    username: StringField = StringField(
        "Username",
        description="awesome_username",
        validators=[validators.Length(min=3, max=25)],
    )
    name: StringField = StringField(
        "Full Name",
        description="John Doe",
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
    redirect_url: HiddenField = HiddenField()


@router.get("/register", response_model=None)
async def register_get(
    request: Request,
    redirect_url: Annotated[str | None, Query(alias="next")] = None,
) -> _TemplateResponse:
    """Return the user registration page."""
    register_form = RegisterUserForm()
    if redirect_url:
        register_form.redirect_url.data = redirect_url
    return templates.TemplateResponse(
        REGISTER_TEMPLATE,
        {constants.REQUEST: request, "form": register_form},
    )


@router.post("/register", response_model=None)
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
                constants.REQUEST: request,
                "message": FormErrorMessage(),
                "form": register_form,
            },
        )
    user_model = db_models.User(
        username=register_form.username.data,
        email=register_form.email.data,
        full_name=register_form.name.data,
        password_hash=auth.hash_password(register_form.password.data),
        role=Role.USER,
        is_active=True,
    )
    db.add(user_model)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        db.rollback()
        if "email" in str(e):
            register_form.email.errors.append("Email already exists for another account.")
        if "username" in str(e):
            register_form.username.errors.append("Username taken.")
        return templates.TemplateResponse(
            REGISTER_TEMPLATE,
            {
                constants.REQUEST: request,
                "message": FormErrorMessage(),
                "form": register_form,
            },
        )
    db.refresh(user_model)
    FlashMessage(
        msg=f"User {user_model.username} created!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        request.url_for("html:login_get").include_query_params(
            username=user_model.username,
            redirect_url=register_form.redirect_url.data,
        ),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/logout", response_model=None)
async def logout(request: Request) -> RedirectResponse:
    """Log the user out and redirect to the home page."""
    form_data = await request.form()
    redirect_url = str(form_data.get("redirect_url", "/"))
    response = RedirectResponse(
        redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(key="access_token", httponly=True)
    FlashMessage(
        msg="You are logged out!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return response


file_ext_validator = validators.regexp(
    r"\.(jpg|jpeg|png|webp|svg)$",
    re.IGNORECASE,
    message="Invalid file extension. Allowed: jpg, jpeg, png, svg, webp",
)


class UserSettingsForm(Form):
    """Form for user settings page."""

    email: StringField = StringField(
        "Email",
        description="new@email.com",
        validators=[validators.Length(min=1, max=25)],
    )
    username: StringField = StringField(
        "Username",
        description="my_new_username",
        validators=[validators.Length(min=3, max=25)],
    )
    name: StringField = StringField(
        "Full Name",
        description="John Doe",
        validators=[validators.Length(min=1, max=25)],
    )
    password: PasswordField = PasswordField(
        "Update Password",
        validators=[validators.optional(), validators.Length(min=8, max=25)],
    )
    confirm_password: PasswordField = PasswordField(
        "Confirm Updated Password",
        validators=[
            validators.EqualTo("password", message="Passwords must match"),
        ],
    )
    timezone: StringField = SelectField(
        "Timezone",
        choices=constants.TIMEZONES,
    )
    avatar_url: StringField = StringField(
        "Remote Avatar URL",
        description="https://example.com/avatar.png",
        validators=[validators.optional(), validators.Length(min=0, max=2000), file_ext_validator],
    )
    avatar_upload: FileField = FileField(
        "Upload Avatar",
        validators=[validators.optional(), file_ext_validator],
    )


@router.get("/user-settings", response_model=None)
async def user_settings_get(
    request: Request,
    current_user: auth.LoggedInUser,
) -> _TemplateResponse:
    """Return the user settings page."""
    form = UserSettingsForm()
    form.email.data = current_user.email
    form.username.data = current_user.username
    form.name.data = current_user.full_name
    form.timezone.data = current_user.timezone
    form.avatar_url.data = current_user.avatar_location
    return templates.TemplateResponse(
        "users/settings.html",
        {constants.REQUEST: request, "form": form, constants.CURRENT_USER: current_user},
    )


@router.post("/user-settings", response_model=None)
async def user_settings_post(
    request: Request,
    current_user: auth.LoggedInUser,
    db: DBSession,
    avatar_upload: UploadFile | None = None,
) -> _TemplateResponse | RedirectResponse:
    """Return the user settings page."""
    form_data = await request.form()
    user_details = {
        "email": form_data.get("email") or current_user.email,
        "username": form_data.get("username") or current_user.username,
        "name": form_data.get("name") or current_user.full_name,
        "timezone": form_data.get("timezone") or current_user.timezone,
        "avatar_url": form_data.get("avatar_url") or current_user.avatar_location,
        "password": form_data.get("password"),
        "confirm_password": form_data.get("confirm_password"),
        "avatar_upload": avatar_upload,
    }
    form = UserSettingsForm(
        **user_details,
    )
    if not form.validate():
        return templates.TemplateResponse(
            "users/settings.html",
            {
                constants.REQUEST: request,
                "message": FormErrorMessage(),
                "form": form,
                constants.CURRENT_USER: current_user,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    await update_user_settings_from_form(form=form, user=current_user)

    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        db.rollback()
        if "email" in str(e):
            form.email.errors.append("Email already exists for another account.")
        if "username" in str(e):
            form.username.errors.append("Username taken.")
        return templates.TemplateResponse(
            "users/settings.html",
            {
                constants.REQUEST: request,
                "message": FormErrorMessage(),
                "form": form,
                constants.CURRENT_USER: current_user,
            },
        )
    db.refresh(current_user)

    FlashMessage(
        msg="Settings updated!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        url=request.url_for("html:user_settings_get"), status_code=status.HTTP_303_SEE_OTHER
    )


async def update_user_settings_from_form(form: UserSettingsForm, user: db_models.User) -> None:  # noqa: C901 (too-complex)
    """Update a user model from a form."""
    if form.password.data:
        user.password_hash = auth.hash_password(form.password.data)
    if form.email.data:
        user.email = form.email.data
    if form.username.data:
        user.username = form.username.data
    if form.name.data:
        user.full_name = form.name.data
    if form.timezone.data:
        user.timezone = form.timezone.data
    avatar_before = user.avatar_location
    if form.avatar_upload.data:
        upload_file = form.avatar_upload.data
        name = f"{user.id}_{uuid4()}"
        user.avatar_location = await media_handler.upload_avatar(pic=upload_file, name=name)
    if form.avatar_url.data and not form.avatar_upload.data:
        user.avatar_location = form.avatar_url.data
    if avatar_before != user.avatar_location:
        media_handler.del_media_from_path_str(avatar_before)
