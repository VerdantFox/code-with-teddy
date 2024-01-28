"""users: API routes for users."""
from typing import cast

from fastapi import APIRouter, status

from app.datastore import db_models
from app.datastore.database import DBSession, Session
from app.permissions import Role
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
)
async def get_users(
    current_user: auth.TokenOptionalUser,
    db: DBSession,
) -> list[db_models.User]:
    """Get users, filtering on the desired fields."""
    query = db.query(db_models.User)
    if not current_user.is_admin:
        query = query.filter(db_models.User.id == current_user.id)
    return cast(list[db_models.User], query.all())


@router.get(
    "/current-user",
    status_code=status.HTTP_200_OK,
    response_model=api_models.UserOutLimited,
)
async def get_current_user(
    current_user: auth.TokenOptionalUser,
) -> db_models.User | UnauthenticatedUser:
    """Get the current user."""
    return current_user


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=api_models.UserOutLimited,
)
async def get_user(
    current_user: auth.TokenRequiredUser,
    user_id: ft.Id,
    db: DBSession,
) -> db_models.User:
    """Get a user by id."""
    return _get_user_by_id(current_user=current_user, user_id=user_id, db=db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=api_models.UserOutLimited,
)
async def create_user(
    user_in: api_models.UserInPost,
    db: DBSession,
) -> db_models.User:
    """Create a user."""
    user_model = db_models.User(
        email=user_in.email,
        username=user_in.username,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        hashed_password=auth.hash_password(user_in.password),
        role=Role.USER,
        is_active=True,
    )
    db.add(user_model)
    db.commit()
    db.refresh(user_model)
    return user_model


@router.patch(
    "/current-user",
    status_code=status.HTTP_200_OK,
    response_model=api_models.UserOutLimited,
)
async def update_current_user(
    current_user: auth.TokenRequiredUser,
    user_in: api_models.UserInPatch,
    db: DBSession,
) -> db_models.User:
    """Update the current user."""
    for field, value in user_in.model_dump(exclude_unset=True).items():
        if field == "password":
            field = "hashed_password"  # noqa: PLW2901 (redefined-loop-name)
            value = auth.hash_password(value)  # noqa: PLW2901 (redefined-loop-name)
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=api_models.UserOutLimited,
)
async def update_user(
    current_user: auth.TokenRequiredUser,
    user_id: ft.Id,
    user_in: api_models.UserInPatch,
    db: DBSession,
) -> db_models.User:
    """Update a user."""
    user_model = _get_user_by_id(current_user=current_user, user_id=user_id, db=db)
    for field, value in user_in.model_dump(exclude_unset=True).items():
        if field == "password":
            field = "hashed_password"  # noqa: PLW2901 (redefined-loop-name)
            value = auth.hash_password(value)  # noqa: PLW2901 (redefined-loop-name)
        setattr(user_model, field, value)
    db.commit()
    db.refresh(user_model)
    return user_model


@router.delete("/current-user", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: auth.TokenRequiredUser,
    db: DBSession,
) -> None:
    """Delete a user."""
    user_model = _get_user_by_id(
        current_user=current_user,
        user_id=current_user.id,
        db=db,
    )
    db.delete(user_model)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    current_user: auth.TokenRequiredUser,
    user_id: ft.Id,
    db: DBSession,
) -> None:
    """Delete a user."""
    user_model = _get_user_by_id(current_user=current_user, user_id=user_id, db=db)
    db.delete(user_model)
    db.commit()


# ----------- Helper functions -----------
def _get_user_by_id(
    current_user: db_models.User,
    user_id: ft.Id,
    db: Session,
) -> db_models.User:
    """Get a user by id."""
    query = db.query(db_models.User).filter(db_models.User.id == user_id)
    if not current_user.is_admin:
        query = query.filter(db_models.User.id == current_user.id)
    if user_model := query.first():
        return user_model
    raise errors.UserNotFoundError
