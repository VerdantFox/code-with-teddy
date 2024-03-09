"""api_models: Pydantic models for the API."""

from pydantic import BaseModel, EmailStr

from app.permissions import Role
from app.web import field_types as ft


# ----------- Error Models -----------
class ErrorOut(BaseModel):
    """Error model for API responses."""

    detail: str | None = None


# ----------- User Models -----------
class UserInPost(BaseModel):
    """User model for POST requests."""

    username: ft.Min3Field
    email: EmailStr
    full_name: ft.Min3Field
    password: ft.Min8Field
    avatar_location: str | None = None
    timezone: str = "UTC"


class UserInPatch(BaseModel):
    """User model for PATCH requests."""

    username: ft.Min3Field | None = None
    email: EmailStr | None = None
    full_name: ft.Min3Field | None = None
    password: ft.Min8Field | None = None
    timezone: str | None = None
    avatar_location: str | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserOutLimited(BaseModel):
    """User model for GET requests.

    Does not include linked models.
    """

    id: int = -1
    username: ft.Min3Field = "unauthenticated"
    email: EmailStr = "unauthenticated@email.com"
    full_name: ft.Min3Field = "Unauthenticated User"
    timezone: str = "UTC"
    avatar_location: str | None = None
    role: Role = Role.UNAUTHENTICATED
    is_active: bool = False


# ----------- Full Models -----------
