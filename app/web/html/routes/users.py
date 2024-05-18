"""users: HTML routes for users."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from starlette.templating import _TemplateResponse
from wtforms import (
    EmailField,
    FileField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    validators,
)

from app import constants
from app.datastore.database import DBSession
from app.services.users import user_handler
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

    email: EmailField = EmailField(
        "Email",
        description="awesome@email.com",
        render_kw={"autocomplete": "username"},
        validators=[validators.Length(min=1, max=100), validators.Email()],
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    register_response = await user_handler.register_user(
        db=db,
        user_input=user_handler.SaveUserInput(
            username=register_form.username.data,
            email=register_form.email.data,
            full_name=register_form.name.data,
            password=register_form.password.data,
        ),
    )
    if not register_response.success:
        for error_field, error_msg in register_response.field_errors.items():
            register_form[error_field].errors.extend(error_msg)
        return templates.TemplateResponse(
            REGISTER_TEMPLATE,
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: register_form,
            },
            status_code=register_response.status_code,
        )

    user = register_response.user
    FlashMessage(
        title="Registration successful!",
        msg=f"username: {user.username}",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        request.url_for("html:login_get").include_query_params(
            username_or_email=user.email,
            next=register_form.redirect_url.data,
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

    email: EmailField = EmailField(
        "Email",
        description="new@email.com",
        validators=[validators.Length(min=1, max=100), validators.Email()],
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
        await db.refresh(current_user)
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

    update_user_response = await user_handler.update_user(
        db=db,
        user_input=user_handler.SaveUserInput(
            existing_user=current_user,
            email=form.email.data,
            username=form.username.data,
            full_name=form.name.data,
            password=form.password.data,
            timezone=form.timezone.data,
            avatar_location=form.avatar_url.data,
            avatar_upload=form.avatar_upload.data,
        ),
    )
    if not update_user_response.success:
        for error_field, error_msg in update_user_response.field_errors.items():
            form[error_field].errors.extend(error_msg)
        return templates.TemplateResponse(
            "users/settings.html",
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: form,
                constants.CURRENT_USER: current_user,
            },
            status_code=update_user_response.status_code,
        )

    FlashMessage(
        title="Settings updated!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        url=request.url_for("html:user_settings_get"), status_code=status.HTTP_303_SEE_OTHER
    )


class PasswordResetRequestForm(Form):
    """Form for password reset request page."""

    email: EmailField = EmailField(
        "Email",
        description="your@emal.com",
        validators=[validators.Length(min=1, max=100), validators.Email()],
    )


@router.get("/request-password-reset", response_model=None)
async def get_request_password_reset(request: Request) -> _TemplateResponse:
    """Return the password reset form."""
    form = PasswordResetRequestForm()
    return templates.TemplateResponse(
        "users/request_password_reset.html",
        {constants.REQUEST: request, constants.FORM: form},
    )


@router.post("/request-password-reset", response_model=None)
async def post_request_password_reset(
    request: Request,
    db: DBSession,
    background_tasks: BackgroundTasks,
) -> _TemplateResponse | RedirectResponse:
    """Send a password reset email."""
    form_data = await request.form()
    form = PasswordResetRequestForm.load(form_data)
    if not form.validate():
        return templates.TemplateResponse(
            "users/request_password_reset.html",
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: form,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    await user_handler.send_pw_reset_email(
        db=db, email=form.email.data, background_tasks=background_tasks
    )
    FlashMessage(
        title="If the email exists, a reset link has been sent.",
        text="Check your email for the reset link.",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        request.url_for("html:get_request_password_reset"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


class PasswordResetForm(Form):
    """Form for password reset page."""

    password: PasswordField = PasswordField(
        "New Password",
        validators=[validators.Length(min=8, max=100)],
    )
    confirm_password: PasswordField = PasswordField(
        "Confirm New Password",
        validators=[
            validators.EqualTo("password", message="Passwords must match"),
        ],
    )


@router.get("/reset-password/{reset_token_query}", response_model=None)
async def get_password_reset(
    request: Request,
    db: DBSession,
    reset_token_query: str,
) -> _TemplateResponse:
    """Return the password reset form."""
    form = PasswordResetForm()
    form.reset_token_query = reset_token_query
    await user_handler.assert_token_is_valid(db=db, query=reset_token_query)

    return templates.TemplateResponse(
        "users/password_reset.html",
        {constants.REQUEST: request, constants.FORM: form, "reset_token_query": reset_token_query},
    )


@router.post("/reset-password/{reset_token_query}", response_model=None)
async def post_password_reset(
    request: Request,
    db: DBSession,
    reset_token_query: str,
) -> _TemplateResponse | RedirectResponse:
    """Reset the user's password."""
    form_data = await request.form()
    form = PasswordResetForm.load(form_data)
    if not form.validate():
        return templates.TemplateResponse(
            "users/password_reset.html",
            {
                constants.REQUEST: request,
                constants.MESSAGE: FormErrorMessage(),
                constants.FORM: form,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    user = await user_handler.reset_password_from_token(
        db=db,
        query=reset_token_query,
        password=form.password.data,
    )
    FlashMessage(
        title="Password reset successful!",
        category=FlashCategory.SUCCESS,
    ).flash(request)
    return RedirectResponse(
        request.url_for("html:login_get").include_query_params(username_or_email=user.email),
        status_code=status.HTTP_303_SEE_OTHER,
    )
