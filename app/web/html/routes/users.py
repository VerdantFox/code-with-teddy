"""users: HTML routes for users."""

from typing import Annotated
from uuid import uuid4

import sqlalchemy
from fastapi import APIRouter, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from starlette.templating import _TemplateResponse
from wtforms import (
    FileField,
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
from app.web.html.wtform_utils import Form, custom_validators

# ----------- Routers -----------
router = APIRouter(tags=["users"])

LOGIN_TEMPLATE = "users/login.html"
REGISTER_TEMPLATE = "users/register.html"


class LoginForm(Form):
    """Form for user login page."""

    username_or_email: StringField = StringField(
        "Username or Email",
        description="awesome@email.com",
        render_kw={"autocomplete": "username"},
        validators=[validators.Length(min=3, max=100)],
    )
    password: PasswordField = PasswordField(
        "Password",
        render_kw={"autocomplete": "current-password"},
        validators=[validators.Length(min=8, max=100)],
    )
    redirect_url: HiddenField = HiddenField()


@router.get("/login", response_model=None)
async def login_get(
    request: Request,
    username_or_email: Annotated[str | None, Query()] = None,
    redirect_url: Annotated[str | None, Query(alias="next")] = None,
) -> _TemplateResponse:
    """Return the login page for GET requests."""
    login_form = LoginForm()
    if username_or_email:
        login_form.username_or_email.data = username_or_email
    if redirect_url:
        login_form.redirect_url.data = redirect_url
    return templates.TemplateResponse(
        LOGIN_TEMPLATE,
        {constants.REQUEST: request, constants.LOGIN_FORM: login_form},
    )


@router.post("/login", response_model=None)
async def login_post(
    request: Request,
    db: DBSession,
) -> _TemplateResponse | RedirectResponse:
    """Log the user in and redirect to the home page."""
    form_data = await request.form()
    login_form = LoginForm.load(form_data)
    if not login_form.validate():
        return templates.TemplateResponse(
            "users/partials/login_form.html",
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.LOGIN_FORM: login_form,
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
            constants.LOGIN_FORM: login_form,
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
                constants.MESSAGE: FormErrorMessage(text=e.detail),
                constants.LOGIN_FORM: login_form,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    FlashMessage(
        title="You are logged in!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return response


class RegisterUserForm(Form):
    """Form for user registration page."""

    email: StringField = StringField(
        "Email",
        description="awesome@email.com",
        render_kw={"autocomplete": "username"},
        validators=[validators.Length(min=1, max=100)],
    )
    username: StringField = StringField(
        "Username",
        description="awesome_username",
        validators=[validators.Length(min=3, max=100)],
    )
    name: StringField = StringField(
        "Full Name",
        description="John Doe",
        validators=[validators.Length(min=1, max=100)],
    )
    password: PasswordField = PasswordField(
        "Password",
        render_kw={"autocomplete": "new-password"},
        validators=[validators.Length(min=8, max=100)],
    )
    confirm_password: PasswordField = PasswordField(
        "Confirm Password",
        render_kw={"autocomplete": "new-password"},
        validators=[
            validators.Length(min=8, max=100),
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
        {constants.REQUEST: request, constants.FORM: register_form},
    )


@router.post("/register", response_model=None)
async def register_post(
    request: Request,
    db: DBSession,
) -> _TemplateResponse | RedirectResponse:
    """Register a new user."""
    form_data = await request.form()
    register_form = RegisterUserForm.load(form_data)
    if not register_form.validate():
        return templates.TemplateResponse(
            REGISTER_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: register_form,
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
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        await db.rollback()
        if 'unique constraint "ix_users_email"' in str(e):
            register_form.email.errors.append("Email already exists for another account.")
        if 'unique constraint "ix_users_username"' in str(e):
            register_form.username.errors.append("Username taken.")
        return templates.TemplateResponse(
            REGISTER_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: register_form,
            },
        )
    await db.refresh(user_model)
    FlashMessage(
        title="Registration successful!",
        msg=f"username: {user_model.username}",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        request.url_for("html:login_get").include_query_params(
            username_or_email=user_model.email,
            redirect_url=register_form.redirect_url.data,
        ),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/logout", response_model=None)
async def logout(request: Request) -> RedirectResponse:
    """Log the user out and redirect to the home page."""
    form_data = await request.form()
    redirect_url = str(form_data.get("next", "/"))
    response = RedirectResponse(
        redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(key="access_token", httponly=True)
    FlashMessage(
        title="You are logged out!",
        category=FlashCategory.INFO,
    ).flash(request)
    return response


AVATAR_EXTENSIONS = ["jpg", "jpeg", "png", "svg", "webp"]


class UserSettingsForm(Form):
    """Form for user settings page."""

    email: StringField = StringField(
        "Email",
        description="new@email.com",
        validators=[validators.Length(min=1, max=100)],
    )
    username: StringField = StringField(
        "Username",
        description="my_new_username",
        validators=[validators.Length(min=3, max=100)],
    )
    name: StringField = StringField(
        "Full Name",
        description="John Doe",
        validators=[validators.Length(min=1, max=100)],
    )
    password: PasswordField = PasswordField(
        "Update Password",
        validators=[validators.Length(min=8, max=100), validators.optional()],
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
        validators=[
            validators.optional(),
            validators.Length(min=1, max=2000),
            custom_validators.is_allowed_extension(AVATAR_EXTENSIONS),
        ],
    )
    avatar_upload: FileField = FileField(
        "Upload Avatar",
        validators=[
            validators.optional(),
            custom_validators.is_allowed_extension(AVATAR_EXTENSIONS),
        ],
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
        {constants.REQUEST: request, constants.FORM: form, constants.CURRENT_USER: current_user},
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
    user_details = dict(form_data) | {"avatar_upload": avatar_upload}
    form = UserSettingsForm.load(user_details)
    if not form.validate():
        return templates.TemplateResponse(
            "users/settings.html",
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: form,
                constants.CURRENT_USER: current_user,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    await update_user_settings_from_form(form=form, user=current_user)

    try:
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        await db.rollback()
        if "email" in str(e):
            form.email.errors.append("Email already exists for another account.")
        if "username" in str(e):
            form.username.errors.append("Username taken.")
        return templates.TemplateResponse(
            "users/settings.html",
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: form,
                constants.CURRENT_USER: current_user,
            },
        )
    await db.refresh(current_user)

    FlashMessage(
        title="Settings updated!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        url=request.url_for("html:user_settings_get"), status_code=status.HTTP_303_SEE_OTHER
    )


async def update_user_settings_from_form(form: UserSettingsForm, user: db_models.User) -> None:
    """Update a user model from a form."""
    if form.password.data:
        user.password_hash = auth.hash_password(form.password.data)
    user.email = form.email.data
    user.username = form.username.data
    user.full_name = form.name.data
    user.timezone = form.timezone.data
    avatar_before = user.avatar_location
    if form.avatar_upload.data:
        upload_file = form.avatar_upload.data
        name = f"{user.id}_{uuid4()}"
        user.avatar_location = await media_handler.upload_avatar(pic=upload_file, name=name)
    if form.avatar_url.data and not form.avatar_upload.data:
        user.avatar_location = form.avatar_url.data
    if not form.avatar_url.data and not form.avatar_upload.data:
        user.avatar_location = None
    if avatar_before and avatar_before != user.avatar_location:
        media_handler.del_media_from_path_str(avatar_before)
