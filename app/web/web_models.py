"""web_models: Pydantic models for the web app."""
from pydantic import BaseModel, EmailStr

import app.web.field_types as ft
from app import mixins
from app.permissions import Role


class UnauthenticatedUser(mixins.AuthUserMixin):
    """Unauthenticated User model."""

    id = -1
    username = "unauthenticated_user"
    is_active = False
    role = Role.UNAUTHENTICATED

    # non-table fields
    is_authenticated: bool = False


class CurrentUser(BaseModel, mixins.AuthUserMixin):
    """Current User model."""

    id: int
    email: EmailStr
    username: ft.Min3Field


class Token(BaseModel):
    """JWT token model."""

    access_token: str
    token_type: str
