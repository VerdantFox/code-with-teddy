"""mixins: Class mixins."""

from app.permissions import Action, Role, permission_map


class AuthUserMixin:
    """Mixin for the User model."""

    # non-table fields
    role: Role
    is_authenticated: bool = True
    guest_id: str = ""

    def is_admin(self) -> bool:
        """Determine if the user is an admin."""
        return self.role == Role.ADMIN

    def has_permission(self, action: Action | str) -> bool:
        """Determine if the user can perform the action."""
        if isinstance(action, str):
            action = Action(action)
        return self.role in permission_map.get(action, set())
