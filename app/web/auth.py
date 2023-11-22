"""auth: Authentication for the web app."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Cookie, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.datastore import db_models
from app.datastore.database import DBSession
from app.web import errors, web_models
from app.web import field_types as ft

# ----------- Constants -----------
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")
optional_oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth", auto_error=False)


# ----------- Imported Dependencies -----------
TokenDependency = Annotated[str, Depends(oauth2_bearer)]
OptionalTokenDependency = Annotated[str | None, Depends(optional_oauth2_bearer)]
OptionalCookieDependency = Annotated[str | None, Cookie()]  # key matches param name


# ----------- User Constants (should be in secrets) -----------
# TODO: Replace with actual password in secrets
SECRET_KEY = "a32739cd7e677c1b8dfcf560a68d59793efdd035fa14dc488192b815d3b5e498"  # noqa: S105 (hardcoded-password-string)
ALGORITHM = "HS256"
TOKEN_EXPIRATION = timedelta(minutes=15)


# ------------ Functions ------------
async def get_current_user_optional_by_cookie(
    db: DBSession,
    access_token: OptionalCookieDependency = None,
) -> db_models.User | web_models.UnauthenticatedUser:
    """Get the current user from the cookie.

    Return an UnauthenticatedUser if no access_token is provided.
    """
    if not access_token:
        return web_models.UnauthenticatedUser()

    return await get_current_user_required_by_token(db=db, access_token=access_token)


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
    return get_user_by_id(user_id, db)


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
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
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
    access_token = jwt.encode(claims=payload, key=SECRET_KEY, algorithm=ALGORITHM)
    return web_models.Token(access_token=access_token, token_type="bearer")  # noqa: S106 (hardcoded-password-func-arg)


def authenticate_user(username: str, password: str, db: DBSession) -> db_models.User:
    """Authenticate a user."""
    user = db.query(db_models.User).filter(db_models.User.username == username).first()
    if not user:
        raise errors.UserNotAuthenticatedError
    if not verify_password(password, user.password_hash):
        raise errors.UserNotAuthenticatedError
    return user


def hash_password(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed version of the password."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_user_by_id(user_id: ft.Id, db: DBSession) -> db_models.User:
    """Get a user by id."""
    if user_model := db.query(db_models.User).filter(db_models.User.id == user_id).first():
        return user_model
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
