"""db_models: SQLAlchemy models for the database."""

from datetime import datetime
from typing import Annotated, ClassVar

import sqlalchemy as sa
from sqlalchemy import Column, Computed, ForeignKey, Index, String, Table, asc
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app import mixins
from app.permissions import Role

# PK types
IntPK = Annotated[int, mapped_column(primary_key=True)]
StrPK = Annotated[str, mapped_column(primary_key=True)]

# String types
StrUnique = Annotated[str, mapped_column(unique=True)]
StrIndexedUnique = Annotated[str, mapped_column(unique=True, index=True)]
StrNullable = Annotated[str | None, mapped_column(nullable=True)]
StrNullableIndexed = Annotated[str | None, mapped_column(nullable=True, index=True)]

# Integer types
IntNullable = Annotated[int | None, mapped_column(nullable=True)]
IntIndexed = Annotated[int, mapped_column(index=True)]
IntIndexedDefaultZero = Annotated[int, mapped_column(index=True, default=0)]

# Validated types
str100 = Annotated[str, 100]

# Boolean types
BoolDefaultFalse = Annotated[bool, mapped_column(default=False)]
BoolDefaultTrue = Annotated[bool, mapped_column(default=True)]

# Datetime types
DateTimeIndexed = Annotated[datetime, mapped_column(index=True)]

# ForeignKey types
UsersFk = Annotated[int, mapped_column(ForeignKey("users.id"), index=True)]
BlogPostFK = Annotated[
    int, mapped_column(ForeignKey("blog_posts.id", ondelete="CASCADE"), index=True)
]
CommentFK = Annotated[int, mapped_column(ForeignKey("blog_post_comments.id"), index=True)]
BPSeriesFK = Annotated[
    int | None, mapped_column(ForeignKey("blog_post_series.id", ondelete="SET NULL"), index=True)
]


class TSVector(sa.types.TypeDecorator):
    """Vector type for PostgreSQL full-text search."""

    impl = TSVECTOR
    cache_ok = True


class Base(AsyncAttrs, DeclarativeBase):
    """Base model for database models."""

    type_annotation_map: ClassVar[dict] = {
        str100: String(100),
    }

    def to_dict(self) -> dict:
        """Return the model as a dictionary."""
        data = self.__dict__.copy()
        data.pop("_sa_instance_state")
        return data


# --------- User models ---------
class User(Base, mixins.AuthUserMixin):
    """User model."""

    __tablename__ = "users"

    id: Mapped[IntPK]
    # User info
    username: Mapped[StrIndexedUnique]
    full_name: Mapped[str]
    email: Mapped[StrIndexedUnique]
    timezone: Mapped[Annotated[str, mapped_column(default="UTC")]]
    is_active: Mapped[BoolDefaultTrue]
    avatar_location: Mapped[StrNullable]

    # Auth stuff
    password_hash: Mapped[StrNullable]
    google_oauth_id: Mapped[StrNullableIndexed]
    github_oauth_id: Mapped[StrNullableIndexed]

    # Permissions
    role: Mapped[Role]

    def __repr__(self) -> str:
        return f"db_models.User(id={self.id}, username={self.username}, role={self.role})"


# --------- Blog models ---------
# Association table for many-to-many relationship between blog posts and tags
blog_tags_associations = Table(
    "blog_tags_associations",
    Base.metadata,
    Column("blog_post_id", ForeignKey("blog_posts.id")),
    Column("blog_post_tag_id", ForeignKey("blog_post_tags.tag")),
)


class BlogPost(Base):
    """Blog post model."""

    __tablename__ = "blog_posts"

    id: Mapped[IntPK]
    title: Mapped[StrIndexedUnique]
    slug: Mapped[StrIndexedUnique]
    old_slugs: Mapped[list["OldBlogPostSlug"]] = relationship(back_populates="blog_post")
    tags: Mapped[list["BlogPostTag"]] = relationship(
        secondary="blog_tags_associations",
        back_populates="blog_posts",
        order_by="asc(BlogPostTag.tag)",
    )
    read_mins: Mapped[IntNullable]
    is_published: Mapped[BoolDefaultFalse]
    can_comment: Mapped[BoolDefaultTrue]
    thumbnail_location: Mapped[StrNullable]

    markdown_description: Mapped[str]
    markdown_content: Mapped[str]
    html_description: Mapped[str]
    html_content: Mapped[str]
    html_toc: Mapped[str]

    media: Mapped[list["BlogPostMedia"]] = relationship(
        back_populates="blog_post",
        order_by="asc(BlogPostMedia.position), asc(BlogPostMedia.created_timestamp)",
    )
    created_timestamp: Mapped[DateTimeIndexed]
    updated_timestamp: Mapped[DateTimeIndexed]
    likes: Mapped[IntIndexed]
    views: Mapped[IntIndexed]
    comments: Mapped[list["BlogPostComment"]] = relationship(
        back_populates="blog_post", order_by="asc(BlogPostComment.created_timestamp)"
    )
    series_id: Mapped[BPSeriesFK | None]
    series_position: Mapped[IntNullable]
    series: Mapped["BlogPostSeries"] = relationship(back_populates="posts")

    ts_vector: Mapped[TSVector] = mapped_column(
        TSVector(),
        Computed("to_tsvector('english', title || ' ' || markdown_content)", persisted=True),
    )
    __table_args__ = (Index("ix_blog_post_ts_vector", ts_vector, postgresql_using="gin"),)


class OldBlogPostSlug(Base):
    """Old blog posts slugs model."""

    __tablename__ = "old_blog_slugs"

    slug: Mapped[StrPK]
    blog_post_id: Mapped[BlogPostFK]
    blog_post: Mapped["BlogPost"] = relationship(back_populates="old_slugs")


class BlogPostTag(Base):
    """Blog post tags model."""

    __tablename__ = "blog_post_tags"

    tag: Mapped[StrPK]
    blog_posts: Mapped[list["BlogPost"]] = relationship(
        secondary="blog_tags_associations", back_populates="tags"
    )


class BlogPostMedia(Base):
    """Blog post media model.

    Might include images or videos.

    Attributes
    ----------
        name: The name of the media, given as the title of the HTML tag.
        locations: The location of the file on the filesystem. If multiple versions
            of the file are included, they are comma-separated.

    """

    __tablename__ = "blog_post_media"

    id: Mapped[IntPK]
    blog_post_id: Mapped[BlogPostFK | None]
    blog_post: Mapped["BlogPost"] = relationship(back_populates="media")
    name: Mapped[str]
    locations: Mapped[str]
    media_type: Mapped[str]
    position: Mapped[int | None]
    created_timestamp: Mapped[DateTimeIndexed]

    def locations_to_list(self) -> list[str]:
        """Get the media locations as a list."""
        return self.locations.split(",")


class BlogPostComment(Base):
    """Blog post comment model."""

    __tablename__ = "blog_post_comments"

    id: Mapped[IntPK]
    blog_post_id: Mapped[BlogPostFK | None]
    blog_post: Mapped["BlogPost"] = relationship(back_populates="comments")
    name: Mapped[StrNullable]  # Name of the commenter
    email: Mapped[StrNullable]  # Email of the commenter
    guest_id: Mapped[StrNullable]  # Guest ID of the commenter
    user_id: Mapped[UsersFk | None]
    user: Mapped["User"] = relationship()
    md_content: Mapped[str]
    html_content: Mapped[str]
    created_timestamp: Mapped[DateTimeIndexed]
    updated_timestamp: Mapped[DateTimeIndexed]
    likes: Mapped[IntIndexedDefaultZero]


class BlogPostSeries(Base):
    """Blog post series model."""

    __tablename__ = "blog_post_series"

    id: Mapped[IntPK]
    name: Mapped[StrIndexedUnique]
    description: Mapped[str]
    posts: Mapped[list[BlogPost]] = relationship(
        back_populates="series",
        order_by=[asc(BlogPost.series_position), asc(BlogPost.created_timestamp)],
    )

    ts_vector: Mapped[TSVector] = mapped_column(
        TSVector(),
        Computed("to_tsvector('english', name || ' ' || description)", persisted=True),
    )
    __table_args__ = (Index("ix_bp_series_ts_vector", ts_vector, postgresql_using="gin"),)


class PasswordResetToken(Base):
    """Password reset token model.

    1) Generate the query string for the token as a UUID4.
    2) Encrypt the query string using the encryption key.
    3) Store the encrypted query string in the database.
    4) Send the query string in the URL to the user's email.
    5) Re-encrypt the query string when the user clicks the link.
    6) Use the re-encrypted query string to find the token in the database.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[IntPK]
    user_id: Mapped[UsersFk]
    # Encrypted query string to be used in the URL to ID this token
    encrypted_query: Mapped[StrIndexedUnique]
    created_timestamp: Mapped[DateTimeIndexed]
    expires_timestamp: Mapped[DateTimeIndexed]
    user: Mapped["User"] = relationship()
