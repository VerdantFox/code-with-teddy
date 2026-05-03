"""permissions: Permissions for the app."""

import inspect
from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

from app import errors

if TYPE_CHECKING:
    from app.mixins import AuthUserMixin


class Role(StrEnum):
    """User roles."""

    UNAUTHENTICATED = "unauthenticated"
    USER = "user"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class Action(StrEnum):
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
        async def wrapper(*args: Any, current_user: AuthUserMixin, **kwargs: Any) -> Any:
            if not current_user.has_permission(permission):
                raise errors.UserPermissionsError
            return await func(*args, current_user=current_user, **kwargs)

        # Expose the original function's signature so FastAPI's dependency
        # injection and OpenAPI schema generation see the correct parameters.
        cast(Any, wrapper).__signature__ = inspect.signature(func)
        return wrapper

    return decorator
