"""permissions: Permissions for the app."""
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING, Any

from app.web import errors

if TYPE_CHECKING:
    from app.mixins import AuthUserMixin


class Role(str, Enum):
    """User roles."""

    UNAUTHENTICATED = "unauthenticated"
    USER = "user"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class Action(str, Enum):
    """Actions that can be performed."""

    EDIT_BP = "edit_bp"
    READ_UNPUBLISHED_BP = "read_unpublished_bp"


permission_map = {
    Action.EDIT_BP: {Role.ADMIN},
    Action.READ_UNPUBLISHED_BP: {Role.REVIEWER, Role.ADMIN},
}


def has_permission(action: Action, role: Role) -> bool:
    """Return whether the role has permission to perform the action."""
    return role in permission_map.get(action, set())


def requires_permission(permission: Action) -> Callable:
    """Decorate a function to require a permission.

    Assumes that the route has a `current_user` parameter,
    which is an instance of `AuthUserMixin`.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, current_user: "AuthUserMixin", **kwargs: Any) -> Any:
            if not current_user.has_permission(permission):
                raise errors.UserPermissionsError
            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator
