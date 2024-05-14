"""auth: Authentication for the web app."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Cookie, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from app.datastore import db_models
from app.datastore.database import DBSession
from app.settings import settings
from app.web import errors, web_models
from app.web import field_types as ft

# ----------- Constants -----------
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")
optional_oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth", auto_error=False)


# ----------- Imported Dependencies -----------
TokenDependency = Annotated[str, Depends(oauth2_bearer)]
OptionalTokenDependency = Annotated[str | None, Depends(optional_oauth2_bearer)]
OptionalCookieDependency = Annotated[str | None, Cookie()]  # key matches param name


# ----------- Constants -----------
TOKEN_EXPIRATION = timedelta(minutes=settings.jwt_expires_mins)


# ------------ Functions ------------
async def get_current_user_optional_by_cookie(
    db: DBSession,
    access_token: OptionalCookieDependency = None,
    guest_id: OptionalCookieDependency = None,
) -> db_models.User | web_models.UnauthenticatedUser:
    """Get the current user from the cookie.

    Return an UnauthenticatedUser if no access_token is provided.
    """
    if access_token:
        current_user: (
            db_models.User | web_models.UnauthenticatedUser
        ) = await get_current_user_required_by_token(db=db, access_token=access_token)
    else:
        current_user = web_models.UnauthenticatedUser()
    guest_id = guest_id or str(uuid.uuid4())
    current_user.guest_id = guest_id
    return current_user


async def get_current_user_required_by_cookie(
    db: DBSession,
    access_token: OptionalCookieDependency = None,
) -> db_models.User | web_models.UnauthenticatedUser:
    """Get the current user from the cookie."""
    if not access_token:
        raise errors.UserNotAuthenticatedError

    return await get_current_user_required_by_token(db=db, access_token=access_token)


async def get_current_user_optional_by_token(
    token: OptionalTokenDependency,
    db: DBSession,
) -> db_models.User | web_models.UnauthenticatedUser:
    """Get the current user from the access_token.

    Return an UnauthenticatedUser if no access_token is provided.
    """
    if token:
        return await get_current_user_required_by_token(db=db, access_token=token)
    return web_models.UnauthenticatedUser()


async def get_current_user_required_by_token(
    db: DBSession,
    access_token: TokenDependency,
) -> db_models.User:
    """Get the current user from the access_token."""
    if not access_token:
        raise errors.UserNotAuthenticatedError

    payload = await parse_access_token(access_token=access_token)
    user_id = int(payload.get("user_id", 0))  # type: ignore[arg-type]
    return await get_user_by_id(user_id, db)


async def refresh_token(
    access_token: str,
    remaining_time: int | None = None,
) -> web_models.Token:
    """Refresh an access token's expiration time.

    Only refresh the token if it has less than time_remaining minutes left.
    """
    payload = await parse_access_token(access_token=access_token)

    if remaining_time is not None:
        current_expires_at_float = float(payload["exp"])  # type: ignore[arg-type]
        current_expires_at = datetime.fromtimestamp(
            current_expires_at_float,
            tz=timezone.utc,
        )
        if current_expires_at - datetime.now(timezone.utc) > timedelta(
            minutes=remaining_time,
        ):
            return encode_access_token(payload=payload)

    new_expires_at = datetime.now(timezone.utc) + TOKEN_EXPIRATION
    payload["exp"] = new_expires_at
    return encode_access_token(payload=payload)


async def parse_access_token(access_token: str) -> dict[str, str | int | datetime]:
    """Parse the access token."""
    try:
        payload = jwt.decode(access_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as e:
        raise errors.UserNotValidatedError from e
    username: str = payload.get("sub", "")
    user_id: int = payload.get("user_id", 0)
    if not all((username, user_id)):
        raise errors.UserNotValidatedError
    return payload


def create_access_token(user: db_models.User) -> web_models.Token:
    """Create an access token for the user."""
    expires_at = datetime.now(timezone.utc) + TOKEN_EXPIRATION
    payload: dict[str, str | int | datetime] = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "exp": expires_at,
    }
    return encode_access_token(payload=payload)


def encode_access_token(payload: dict[str, str | int | datetime]) -> web_models.Token:
    """Encode a JWT access token from a payload."""
    access_token = jwt.encode(
        payload=payload, key=settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return web_models.Token(access_token=access_token, token_type="bearer")  # noqa: S106 (hardcoded-password-func-arg)


async def authenticate_user(username_or_email: str, password: str, db: DBSession) -> db_models.User:
    """Authenticate a user."""
    if "@" in username_or_email:
        stmt = select(db_models.User).filter(db_models.User.email == username_or_email)
    else:
        stmt = select(db_models.User).filter(db_models.User.username == username_or_email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise errors.UserNotAuthenticatedError
    if not verify_password(password, user.password_hash):
        raise errors.UserNotAuthenticatedError
    return user


def hash_password(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plain password against a hashed version of the password."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


async def get_user_by_id(user_id: ft.Id, db: DBSession) -> db_models.User:
    """Get a user by id."""
    stmt = select(db_models.User).filter(db_models.User.id == user_id)
    result = await db.execute(stmt)
    if user := result.scalars().first():
        return user
    raise errors.UserNotFoundError


#  ----------- Exported Dependencies -----------
TokenRequiredUser = Annotated[
    db_models.User,
    Depends(get_current_user_required_by_token),
]
TokenOptionalUser = Annotated[
    db_models.User | web_models.UnauthenticatedUser,
    Depends(get_current_user_optional_by_token),
]
LoggedInUserOptional = Annotated[
    db_models.User | web_models.UnauthenticatedUser,
    Depends(get_current_user_optional_by_cookie),
]
LoggedInUser = Annotated[db_models.User, Depends(get_current_user_required_by_cookie)]
