"""api_models: Pydantic models for the API."""
from pydantic import BaseModel, EmailStr

from app.permissions import Role
from app.web import field_types as ft


# ----------- User Models -----------
class UserInPost(BaseModel):
    """User model for POST requests."""

    email: EmailStr
    username: ft.Min3Field
    first_name: ft.Min3Field
    last_name: ft.Min3Field
    password: ft.Min8Field


class UserInPatch(BaseModel):
    """User model for PATCH requests."""

    email: EmailStr | None = None
    username: ft.Min3Field | None = None
    first_name: ft.Min3Field | None = None
    last_name: ft.Min3Field | None = None
    password: ft.Min8Field | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserOutLimited(BaseModel):
    """User model for GET requests.

    Does not include linked models.
    """

    id: int = -1
    email: EmailStr = "unauthenticated@email.com"
    username: ft.Min3Field = "unauthenticated"
    first_name: ft.Min3Field = "unauthenticated"
    last_name: ft.Min3Field = "unauthenticated"
    role: Role = Role.UNAUTHENTICATED
    is_active: bool = False


# ----------- Full Models -----------
