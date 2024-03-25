"""test_blog_edit_post: test edit blog post POST endpoint."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import TestCase
from tests.data import models as test_models


@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module."""


@pytest.fixture(autouse=True)
async def _clean_db_fixture_function(clean_db_except_users: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each function."""


def test_edit_blog_post_as_guest_fails(test_client: TestClient):
    """Test that a guest cannot edit a blog post."""
    response = test_client.post("/blog/1/edit", data={})
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_edit_blog_post_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot edit a blog post."""
    response = test_client.post("/blog/1/edit", data={})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


class EditPostTestCase(TestCase):
    """Test case for editing a blog post."""

    # RUF012: Mutable class strings should have typing.ClassVar
    # But these are from pydantic.BaseModel, so they are allowed to be mutable
    bp_id: int | str | None = None
    data: dict[str, str] = {}  # noqa: RUF012
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012


# Form fields
IS_NEW = "is_new"
TITLE = "title"
TAGS = "tags"
CAN_COMMENT = "can_comment"
IS_PUBLISHED = "is_published"
DESCRIPTION = "description"
CONTENT = "content"
THUMBNAIL_URL = "thumbnail_url"

# Form field values
BLANK = ""
TRUE = "true"
FALSE = "false"
TITLE_VAL = "Updated title"
TAGS_VAL = "updated_tag, updated_tag2"
DESCRIPTION_MD = "updated description"
CONTENT_MD = "updated content"

# Others
CONTENT_HTML = "<p>updated content</p>"

DEFAULT_DATA = {
    IS_NEW: FALSE,
    TITLE: TITLE_VAL,
    TAGS: TAGS_VAL,
    CAN_COMMENT: FALSE,
    IS_PUBLISHED: FALSE,
    DESCRIPTION: DESCRIPTION_MD,
    CONTENT: CONTENT_MD,
    THUMBNAIL_URL: BLANK,
}
OG_TITLE = test_models.BASIC_BLOG_POST[test_models.BlogPostInputKeys.TITLE]
OG_DESCRIPTION = test_models.BASIC_BLOG_POST[test_models.BlogPostInputKeys.DESCRIPTION]
OG_CONTENT = test_models.BASIC_BLOG_POST[test_models.BlogPostInputKeys.CONTENT]
OG_THUMBNAIL_URL = test_models.BASIC_BLOG_POST[test_models.BlogPostInputKeys.THUMBNAIL_URL]

EDIT_POST_TEST_CASES = [
    EditPostTestCase(
        id="happy_path",
        data=DEFAULT_DATA,
        expected_strings=[TITLE_VAL, DESCRIPTION_MD, CONTENT_MD, CONTENT_HTML],
    ),
    EditPostTestCase(
        id="opposites",
        data={
            IS_NEW: FALSE,
            TITLE: OG_TITLE,
            TAGS: BLANK,
            CAN_COMMENT: TRUE,
            IS_PUBLISHED: TRUE,
            DESCRIPTION: OG_DESCRIPTION,
            CONTENT: OG_CONTENT,
            THUMBNAIL_URL: OG_THUMBNAIL_URL,
        },
        expected_strings=[OG_TITLE, OG_DESCRIPTION, OG_CONTENT],
    ),
    EditPostTestCase(
        id="no_data",
        data={},
        expected_strings=[
            "Invalid form field(s). See errors on form.",
            "Field must be at least 1 character long.",
        ],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    EditPostTestCase(
        id="missing_bp",
        bp_id=999,
        data=DEFAULT_DATA,
        expected_strings=["404 Error", "Blog post not found"],
        expected_status_code=status.HTTP_404_NOT_FOUND,
    ),
]


@pytest.mark.usefixtures("logged_in_admin_user_module")
@EditPostTestCase.parametrize(EDIT_POST_TEST_CASES)
def test_edit_blog_post_as_admin(
    test_client: TestClient,
    basic_blog_post: db_models.BlogPost,
    test_case: EditPostTestCase,
):
    """Test that an admin user can edit a blog post."""
    bp = basic_blog_post
    bp_id = test_case.bp_id or bp.id
    response = test_client.post(f"/blog/{bp_id}/edit", data=test_case.data)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_edit_blog_post_repeat_title_fails(
    test_client: TestClient,
    basic_blog_post: db_models.BlogPost,
    advanced_blog_post: db_models.BlogPost,
):
    """Test that an admin user cannot edit a blog post with a title that already exists."""
    basic_bp = basic_blog_post
    advanced_bp = advanced_blog_post
    data = {**DEFAULT_DATA, TITLE: advanced_bp.title}
    response = test_client.post(f"/blog/{basic_bp.id}/edit", data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Error saving blog post" in response.text
    assert "Title already exists" in response.text
