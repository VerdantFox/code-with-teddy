"""users: API routes for users."""

from typing import cast

import sqlalchemy
from fastapi import APIRouter, status
from sqlalchemy import select

from app.datastore import db_models
from app.datastore.database import AsyncSession, DBSession
from app.permissions import Role
from app.services.general import auth_helpers
from app.web import auth, errors
from app.web import field_types as ft
from app.web.api import api_models
from app.web.web_models import UnauthenticatedUser

# ----------- Routers -----------
router = APIRouter(tags=["users"], prefix="/users")


# ----------- User routes -----------
@router.get(
    "",
    response_model=list[api_models.UserOutLimited],
    status_code=status.HTTP_200_OK,
    responses={401: {"model": api_models.ErrorOut}},
)
async def get_users(
    current_user: auth.TokenOptionalUser,
    db: DBSession,
) -> list[db_models.User]:
    """Get users, filtering on the desired fields."""
    stmt = select(db_models.User)
    if not current_user.is_admin:
        stmt = stmt.filter(db_models.User.id == current_user.id)
    results = await db.execute(stmt)

    return cast(list[db_models.User], results.scalars().all())


@router.get(
    "/current-user",
    response_model=api_models.UserOutLimited,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": api_models.ErrorOut}},
)
async def get_current_user(
    current_user: auth.TokenOptionalUser,
) -> db_models.User | UnauthenticatedUser:
    """Get the current user."""
    return current_user


@router.get(
    "/{user_id}",
    response_model=api_models.UserOutLimited,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": api_models.ErrorOut}, 404: {"model": api_models.ErrorOut}},
)
async def get_user(
    current_user: auth.TokenRequiredUser,
    user_id: ft.Id,
    db: DBSession,
) -> db_models.User:
    """Get a user by id."""
    return await _get_user_by_id(current_user=current_user, user_id=user_id, db=db)


@router.post(
    "",
    response_model=api_models.UserOutLimited,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": api_models.ErrorOut}, 403: {"model": api_models.ErrorOut}},
)
async def create_user(
    current_user: auth.TokenRequiredUser,
    user_in: api_models.UserInPost,
    db: DBSession,
) -> db_models.User:
    """Create a user."""
    if not current_user.is_admin:
        raise errors.UserPermissionsError
    user_model = db_models.User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=auth_helpers.hash_password(user_in.password),
        role=Role.USER,
        is_active=True,
        timezone=user_in.timezone,
        avatar_location=user_in.avatar_location,
    )
    db.add(user_model)
    try:
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        if "ix_users_username" in str(e):
            err_msg = f"User with username '{user_in.username}' already exists."
            raise errors.UserAlreadyExistsError(err_msg) from e
        if "ix_users_email" in str(e):
            err_msg = f"User with email '{user_in.email}' already exists."
            raise errors.UserAlreadyExistsError(err_msg) from e
        raise errors.UserAlreadyExistsError from e  # pragma: no cover (should be caught above)
    await db.refresh(user_model)
    return user_model


@router.patch(
    "/current-user",
    response_model=api_models.UserOutLimited,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": api_models.ErrorOut}},
)
async def update_current_user(
    current_user: auth.TokenRequiredUser,
    user_in: api_models.UserInPatch,
    db: DBSession,
) -> db_models.User:
    """Update the current user."""
    for field, value in user_in.model_dump(exclude_unset=True).items():
        if field == "role" and not current_user.is_admin:
            err_msg = "Cannot update role field"
            raise errors.UserPermissionsError(err_msg)
        if field == "password":
            field = "password_hash"  # noqa: PLW2901 (redefined-loop-name)
            value = auth_helpers.hash_password(value)  # noqa: PLW2901 (redefined-loop-name)
        setattr(current_user, field, value)
    try:
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        if "ix_users_username" in str(e):
            err_msg = f"User with username '{user_in.username}' already exists."
            raise errors.UserAlreadyExistsError(err_msg) from e
        if "ix_users_email" in str(e):
            err_msg = f"User with email '{user_in.email}' already exists."
            raise errors.UserAlreadyExistsError(err_msg) from e
        raise errors.UserAlreadyExistsError from e  # pragma: no cover (should be caught above)
    await db.refresh(current_user)
    return current_user


@router.patch(
    "/{user_id}",
    response_model=api_models.UserOutLimited,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": api_models.ErrorOut}, 404: {"model": api_models.ErrorOut}},
)
async def update_user(
    current_user: auth.TokenRequiredUser,
    user_id: ft.Id,
    user_in: api_models.UserInPatch,
    db: DBSession,
) -> db_models.User:
    """Update a user."""
    user_model = await _get_user_by_id(current_user=current_user, user_id=user_id, db=db)
    for field, value in user_in.model_dump(exclude_unset=True).items():
        if field == "role" and not current_user.is_admin:
            err_msg = "Cannot update role field"
            raise errors.UserPermissionsError(err_msg)
        if field == "password":
            field = "password_hash"  # noqa: PLW2901 (redefined-loop-name)
            value = auth_helpers.hash_password(value)  # noqa: PLW2901 (redefined-loop-name)
        setattr(user_model, field, value)
    try:
        await db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        if "ix_users_username" in str(e):
            err_msg = f"User with username '{user_in.username}' already exists."
            raise errors.UserAlreadyExistsError(err_msg) from e
        if "ix_users_email" in str(e):
            err_msg = f"User with email '{user_in.email}' already exists."
            raise errors.UserAlreadyExistsError(err_msg) from e
        raise errors.UserAlreadyExistsError from e  # pragma: no cover (should be caught above)
    await db.refresh(user_model)
    return user_model


@router.delete(
    "/current-user",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": api_models.ErrorOut}},
)
async def delete_current_user(
    current_user: auth.TokenRequiredUser,
    db: DBSession,
) -> None:
    """Delete a user."""
    user_model = await _get_user_by_id(
        current_user=current_user,
        user_id=current_user.id,
        db=db,
    )
    await db.delete(user_model)
    await db.commit()


@router.delete(
    "/{user_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": api_models.ErrorOut}, 404: {"model": api_models.ErrorOut}},
)
async def delete(
    current_user: auth.TokenRequiredUser,
    user_id: ft.Id,
    db: DBSession,
) -> None:
    """Delete a user."""
    user_model = await _get_user_by_id(current_user=current_user, user_id=user_id, db=db)
    await db.delete(user_model)
    await db.commit()


# ----------- Helper functions -----------
async def _get_user_by_id(
    current_user: db_models.User,
    user_id: ft.Id,
    db: AsyncSession,
) -> db_models.User:
    """Get a user by id."""
    stmt = select(db_models.User).filter(db_models.User.id == user_id)
    if not current_user.is_admin:
        stmt = stmt.filter(db_models.User.id == current_user.id)
    results = await db.execute(stmt)
    if user_model := results.scalars().first():
        return user_model
    raise errors.UserNotFoundError
