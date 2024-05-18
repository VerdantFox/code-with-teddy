"""user_handler: functions and classes for handling users."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from logging import getLogger
from uuid import uuid4

import sqlalchemy
from fastapi import BackgroundTasks, UploadFile
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.datastore import db_models
from app.permissions import Role
from app.services.general import auth_helpers, email_handler, encryption_handler
from app.services.media import media_handler
from app.web import errors

logger = getLogger(__name__)
PW_RESET_TOKEN_EXPIRATION_MINUTES = 1


class SaveUserInput(BaseModel, arbitrary_types_allowed=True):
    """Input data model for saving a user."""

    existing_user: db_models.User | None = None
    username: str
    full_name: str
    email: EmailStr
    timezone: str = "UTC"
    is_active: bool = True
    avatar_location: str | None = None
    avatar_upload: UploadFile | None = None
    password: str | None = None
    google_oauth_id: str | None = None
    github_oauth_id: str | None = None
    role: Role = Role.USER


class SaveUserResponse(BaseModel, arbitrary_types_allowed=True):
    """Response for saving a user."""

    success: bool = True
    user: db_models.User
    status_code: HTTPStatus = HTTPStatus.OK
    field_errors: defaultdict[str, list[str]] = defaultdict(list)


async def register_user(
    db: AsyncSession,
    user_input: SaveUserInput,
) -> SaveUserResponse:
    """Register a new user."""
    assert user_input.password, "Password is required."  # noqa: S101 (assert-used -- password is guaranteed to be set)
    user = db_models.User(
        username=user_input.username,
        email=user_input.email,
        full_name=user_input.full_name,
        password_hash=auth_helpers.hash_password(user_input.password),
        role=Role.USER,
        is_active=True,
    )
    db.add(user)
    field_errors: defaultdict[str, list[str]] = defaultdict(list)
    try:
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        await db.rollback()
        if 'unique constraint "ix_users_email"' in str(e):
            field_errors["email"].append("Email already exists for another account.")
        if 'unique constraint "ix_users_username"' in str(e):
            field_errors["username"].append("Username taken.")
        return SaveUserResponse(
            success=False,
            user=user,
            status_code=HTTPStatus.BAD_REQUEST,
            field_errors=field_errors,
        )
    await db.refresh(user)
    return SaveUserResponse(user=user)


async def update_user(
    db: AsyncSession,
    user_input: SaveUserInput,
) -> SaveUserResponse:
    """Update a user."""
    user = user_input.existing_user
    assert user, "User is required."  # noqa: S101 (assert-used -- user is guaranteed to be set)
    user = await update_user_settings_fields(user_input, user)
    db.add(user)
    field_errors: defaultdict[str, list[str]] = defaultdict(list)

    try:
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        await db.rollback()
        await db.refresh(user)
        if "ix_users_email" in str(e):
            field_errors["email"].append("Email already exists for another account.")
        if "ix_users_username" in str(e):
            field_errors["username"].append("Username taken.")
        return SaveUserResponse(
            success=False,
            user=user,
            status_code=HTTPStatus.BAD_REQUEST,
            field_errors=field_errors,
        )
    await db.refresh(user)
    return SaveUserResponse(user=user)


async def update_user_settings_fields(
    user_input: SaveUserInput, user: db_models.User
) -> db_models.User:
    """Update a user model from a user_input."""
    if user_input.password:
        user.password_hash = auth_helpers.hash_password(user_input.password)
    user.email = user_input.email
    user.username = user_input.username
    user.full_name = user_input.full_name
    user.timezone = user_input.timezone
    avatar_before = user.avatar_location
    if user_input.avatar_upload:
        upload_file = user_input.avatar_upload
        name = f"{user.id}_{uuid4()}"
        user.avatar_location = await media_handler.upload_avatar(pic=upload_file, name=name)
    if user_input.avatar_location and not user_input.avatar_upload:
        user.avatar_location = user_input.avatar_location
    if not user_input.avatar_location and not user_input.avatar_upload:
        user.avatar_location = None
    if avatar_before and avatar_before != user.avatar_location:
        media_handler.del_media_from_path_str(avatar_before)
    return user


async def send_pw_reset_email(
    db: AsyncSession, email: str, background_tasks: BackgroundTasks
) -> None:
    """Send a password reset email."""
    try:
        user = await get_user_by_email(db, email)
    except sqlalchemy.exc.NoResultFound:
        logger.info("User not found for email: %s", email)
        return
    query, _ = await create_pw_reset_token(db, user)
    background_tasks.add_task(email_handler.send_pw_reset_email_to_user, user=user, query=query)


async def get_user_by_email(db: AsyncSession, email: str) -> db_models.User:
    """Get a user by email."""
    stmt = select(db_models.User).where(db_models.User.email == email)
    result = await db.execute(stmt)
    return result.scalars().one()


async def create_pw_reset_token(
    db: AsyncSession, user: db_models.User
) -> tuple[str, db_models.PasswordResetToken]:
    """Create a password reset token."""
    # Delete any existing tokens related to this user
    stmt = delete(db_models.PasswordResetToken).where(
        db_models.PasswordResetToken.user_id == user.id
    )
    await db.execute(stmt)

    # Delete any existing tokens older than PW_RESET_TOKEN_EXPIRATION_MINUTES
    stmt = delete(db_models.PasswordResetToken).where(
        db_models.PasswordResetToken.created_timestamp
        < datetime.now().astimezone(timezone.utc)
        - timedelta(minutes=PW_RESET_TOKEN_EXPIRATION_MINUTES)
    )
    await db.execute(stmt)

    # Create new token
    query = str(uuid4())
    pw_reset_token = db_models.PasswordResetToken(
        user_id=user.id,
        encrypted_query=encryption_handler.encrypt(query),
        created_timestamp=datetime.now().astimezone(timezone.utc),
        expires_timestamp=datetime.now().astimezone(timezone.utc)
        + timedelta(minutes=PW_RESET_TOKEN_EXPIRATION_MINUTES),
    )
    db.add(pw_reset_token)
    await db.commit()

    return query, pw_reset_token


async def assert_token_is_valid(db: AsyncSession, query: str) -> db_models.PasswordResetToken:
    """Get a password reset token by query."""
    encrypted_query = encryption_handler.encrypt(query)

    stmt = select(db_models.PasswordResetToken).where(
        db_models.PasswordResetToken.encrypted_query == encrypted_query
    )
    result = await db.execute(stmt)
    try:
        token = result.scalars().one()
    except sqlalchemy.orm.exc.NoResultFound as e:
        raise errors.PasswordResetTokenNotFoundError from e
    token_dt = token.expires_timestamp.astimezone(timezone.utc)
    if token_dt < datetime.now().astimezone(timezone.utc):
        raise errors.PasswordResetTokenExpiredError
    return token


async def reset_password_from_token(db: AsyncSession, query: str, password: str) -> db_models.User:
    """Reset a user's password from a password reset token."""
    encrypted_query = encryption_handler.encrypt(query)

    get_token_stmt = select(db_models.PasswordResetToken).where(
        db_models.PasswordResetToken.encrypted_query == encrypted_query
    )
    get_token_result = await db.execute(get_token_stmt)
    try:
        pw_reset_token = get_token_result.scalars().one()
    except sqlalchemy.orm.exc.NoResultFound as e:
        raise errors.PasswordResetTokenNotFoundError from e
    token_dt = pw_reset_token.expires_timestamp.astimezone(timezone.utc)
    if token_dt < datetime.now().astimezone(timezone.utc):
        raise errors.PasswordResetTokenExpiredError
    get_user_stmt = select(db_models.User).where(db_models.User.id == pw_reset_token.user_id)
    get_user_result = await db.execute(get_user_stmt)
    try:
        user = get_user_result.scalars().one()
    except sqlalchemy.orm.exc.NoResultFound as e:
        raise errors.UserNotFoundError from e
    user.password_hash = auth_helpers.hash_password(password)
    db.add(user)
    await db.delete(pw_reset_token)
    await db.commit()
    await db.refresh(user)
    return user
