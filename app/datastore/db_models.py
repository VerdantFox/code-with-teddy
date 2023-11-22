"""db_models: SQLAlchemy models for the database."""
from typing import Annotated, ClassVar

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from app import mixins
from app.permissions import Role

IntPK = Annotated[int, mapped_column(primary_key=True)]
UniqueStr = Annotated[str, mapped_column(unique=True)]
UsersFk = Annotated[int, mapped_column(ForeignKey("users.id"))]
str100 = Annotated[str, 100]


class Base(DeclarativeBase):
    """Base model for database models."""

    type_annotation_map: ClassVar[dict] = {
        str100: String(100),
    }


class User(Base, mixins.AuthUserMixin):
    """User model."""

    __tablename__ = "users"

    id: Mapped[IntPK]
    username: Mapped[UniqueStr]
    email: Mapped[UniqueStr]
    full_name: Mapped[str]
    timezone: Mapped[str]

    password_hash: Mapped[str]
    google_oauth_id: Mapped[str] = mapped_column(nullable=True)
    github_oauth_id: Mapped[str] = mapped_column(nullable=True)

    role: Mapped[Role]
    is_active: Mapped[bool] = mapped_column(default=False)
