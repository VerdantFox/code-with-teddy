"""models: models for use in tests."""

import enum
from typing import Any

from app.datastore import db_models
from app.permissions import Role
from app.services.blog import blog_handler
from app.services.general import auth_helpers


class UserModelKeys(str, enum.Enum):
    """User model keys."""

    ID = "id"
    USERNAME = "username"
    FULL_NAME = "full_name"
    EMAIL = "email"
    TIMEZONE = "timezone"
    IS_ACTIVE = "is_active"
    AVATAR_LOCATION = "avatar_location"
    PASSWORD_HASH = "password_hash"
    GOOGLE_OAUTH_ID = "google_oauth_id"
    GITHUB_OAUTH_ID = "github_oauth_id"
    ROLE = "role"
    PASSWORD = "password"


PASSWORD_VAL = "password1"
BASIC_USER = {
    UserModelKeys.USERNAME: "test_user",
    UserModelKeys.EMAIL: "test@email.com",
    UserModelKeys.FULL_NAME: "Test User",
    UserModelKeys.IS_ACTIVE: True,
    UserModelKeys.PASSWORD: PASSWORD_VAL,
    UserModelKeys.PASSWORD_HASH: auth_helpers.hash_password(PASSWORD_VAL),
    UserModelKeys.ROLE: Role.USER,
}


def basic_user(**kwargs: Any) -> db_models.User:
    """Return a basic user."""
    user_dict = {key.value: value for key, value in BASIC_USER.items()}
    user_dict |= kwargs
    user_dict.pop(UserModelKeys.PASSWORD.value)
    return db_models.User(**user_dict)


ADMIN_USER = {
    UserModelKeys.USERNAME: "admin_user",
    UserModelKeys.EMAIL: "admin@email.com",
    UserModelKeys.FULL_NAME: "Admin User",
    UserModelKeys.IS_ACTIVE: True,
    UserModelKeys.ROLE: Role.ADMIN,
    UserModelKeys.PASSWORD: PASSWORD_VAL,
    UserModelKeys.PASSWORD_HASH: auth_helpers.hash_password(PASSWORD_VAL),
}


def admin_user() -> db_models.User:
    """Return an admin user."""
    user_dict = {key.value: value for key, value in ADMIN_USER.items()}
    user_dict.pop(UserModelKeys.PASSWORD.value)
    return db_models.User(**user_dict)


class BlogPostKeys(str, enum.Enum):
    """Blog post keys."""

    ID = "id"
    TITLE = "title"
    SLUG = "slug"
    OLD_SLUGS = "old_slugs"
    TAGS = "tags"
    READ_MINS = "read_mins"
    IS_PUBLISHED = "is_published"
    CAN_COMMENT = "can_comment"
    THUMBNAIL_LOCATION = "thumbnail_location"
    MARKDOWN_DESCRIPTION = "markdown_description"
    MARKDOWN_CONTENT = "markdown_content"
    HTML_DESCRIPTION = "html_description"
    HTML_CONTENT = "html_content"
    HTML_TOC = "html_toc"
    MEDIA = "media"
    CREATED_TIMESTAMP = "created_timestamp"
    UPDATED_TIMESTAMP = "updated_timestamp"
    LIKES = "likes"
    VIEWS = "views"
    COMMENTS = "comments"
    TS_VECTOR = "ts_vector"


class BlogPostInputKeys(str, enum.Enum):
    """Blog post input keys."""

    TITLE = "title"
    TAGS = "tags"
    CAN_COMMENT = "can_comment"
    IS_PUBLISHED = "is_published"
    DESCRIPTION = "description"
    CONTENT = "content"
    THUMBNAIL_URL = "thumbnail_url"
    LIKES = "likes"
    VIEWS = "views"


BASIC_BLOG_POST = {
    BlogPostInputKeys.TITLE: "Test Blog Post",
    BlogPostInputKeys.CAN_COMMENT: True,
    BlogPostInputKeys.IS_PUBLISHED: True,
    BlogPostInputKeys.DESCRIPTION: "This is a test blog post.",
    BlogPostInputKeys.CONTENT: "This is the content of a test blog post.",
    BlogPostInputKeys.THUMBNAIL_URL: "https://foo/bar.png",
}


def basic_blog_post(**kwargs: Any) -> blog_handler.SaveBlogInput:
    """Return a simple blog post."""
    blog_post_dict = {key.value: value for key, value in BASIC_BLOG_POST.items()}
    blog_post_dict |= kwargs
    return blog_handler.SaveBlogInput(**blog_post_dict)


ADVANCED_BLOG_POST = BASIC_BLOG_POST.copy()
ADVANCED_BLOG_POST[BlogPostInputKeys.TITLE] = "Advanced Blog Post"
ADVANCED_BLOG_POST[BlogPostInputKeys.TAGS] = ["test", "python"]
ADVANCED_BLOG_POST[BlogPostInputKeys.THUMBNAIL_URL] = (
    "https://upload.wikimedia.org/wikipedia/en/0/00/WoT01_TheEyeOfTheWorld.jpg"
)
ADVANCED_BLOG_POST[BlogPostInputKeys.LIKES] = 32
ADVANCED_BLOG_POST[BlogPostInputKeys.VIEWS] = 123


def advanced_blog_post() -> blog_handler.SaveBlogInput:
    """Return an advanced blog post."""
    blog_post_dict = {key.value: value for key, value in ADVANCED_BLOG_POST.items()}
    return blog_handler.SaveBlogInput(**blog_post_dict)
