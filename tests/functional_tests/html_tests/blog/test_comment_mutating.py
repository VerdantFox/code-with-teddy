"""test_comment_mutating: test various mutating comment endpoints."""

import re

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import TestCase


# NOTE: Can't use module scoped users because some fixtures rely on function-scoped users
@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db: None, anyio_backend: str) -> None:
    """Clean the database after each test."""


# ------------------------ post new comment ------------------------
class PostCommentTestCase(TestCase):
    """Test case for posting comments."""

    # RUF012: Mutable class strings should have typing.ClassVar
    # But these are from pydantic.BaseModel, so they are allowed to be mutable
    bp_id: int | str | None = None
    data: dict[str, str] = {}  # noqa: RUF012
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012


# Fields
CHECK_ME = "check_me"
NOT_ROBOT = "not_robot"
NAME = "name"
EMAIL = "email"
CONTENT = "content"

# Field values
PERRIN = "Perrin Aybara"
PERRIN_EMAIL = "perrin@email.com"
BASIC_CONTENT_MD = "some content"
UPDATED_CONTENT_MD = "updated content"
BLANK = ""
TRUE = "true"
FALSE = "false"

# Page strings
BASIC_CONTENT_HTML = "<p>some content</p>"
UPDATED_CONTENT_HTML = "<p>updated content</p>"
INVALID_FORM = "Invalid form field(s). See errors on form."


NEW_COMMENT_TEST_CASES = [
    PostCommentTestCase(
        id="basic_with_email",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PERRIN, BASIC_CONTENT_HTML],
    ),
    PostCommentTestCase(
        id="basic_with_bad_email",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: "not-an-email",
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["Invalid email address.", PERRIN, BASIC_CONTENT_MD],
    ),
    PostCommentTestCase(
        id="basic_no_email",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: BLANK,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PERRIN, BASIC_CONTENT_HTML],
    ),
    PostCommentTestCase(
        id="fail_honey_pot",
        data={
            CHECK_ME: TRUE,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["No robots allowed!", PERRIN, BASIC_CONTENT_MD],
    ),
    PostCommentTestCase(
        id="fail_not_robot",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: FALSE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["No robots allowed!", PERRIN, BASIC_CONTENT_MD],
    ),
    PostCommentTestCase(
        id="no_name",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: BLANK,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=[INVALID_FORM, BASIC_CONTENT_MD],
    ),
    PostCommentTestCase(
        id="no_content",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BLANK,
        },
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["This field is required.", INVALID_FORM],
    ),
    # Advanced MD test cases covered by `test_comment_post_preview_as_guest`
]


@PostCommentTestCase.parametrize(NEW_COMMENT_TEST_CASES)
def test_post_new_comment_as_guest(
    test_client: TestClient,
    basic_blog_post: db_models.BlogPost,
    test_case: PostCommentTestCase,
):
    """Test posting a new comment."""
    bp = basic_blog_post
    bp_id = test_case.bp_id or bp.id

    response = test_client.post(f"/blog/{bp_id}/comment", data=test_case.data)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text


def test_comment_as_basic_user(
    test_client: TestClient,
    basic_blog_post: db_models.BlogPost,
    logged_in_basic_user: db_models.User,
):
    """Test posting a new comment as a basic user."""
    bp = basic_blog_post
    bp_id = bp.id
    data = {CONTENT: BASIC_CONTENT_MD}

    response = test_client.post(f"/blog/{bp_id}/comment", data=data)
    assert response.status_code == status.HTTP_200_OK
    assert logged_in_basic_user.full_name in response.text
    assert BASIC_CONTENT_HTML in response.text
    assert "Comments (1)" in response.text


@pytest.mark.usefixtures("logged_in_basic_user")
def test_comment_as_basic_user_with_bp_cannot_comment_fails(
    test_client: TestClient, blog_post_cannot_comment: db_models.BlogPost
):
    """Test posting a new comment as a basic user on a blog post that cannot be commented on."""
    bp = blog_post_cannot_comment
    bp_id = bp.id
    data = {CONTENT: BASIC_CONTENT_MD}

    response = test_client.post(f"/blog/{bp_id}/comment", data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Commenting has been disabled for this blog post..." in response.text


@pytest.mark.usefixtures("logged_in_admin_user")
def test_comment_as_admin_user_with_bp_cannot_comment_succeeds(
    test_client: TestClient, blog_post_cannot_comment: db_models.BlogPost
):
    """Test posting a new comment as an admin user on a blog post that cannot be commented on succeeds."""
    bp = blog_post_cannot_comment
    bp_id = bp.id
    data = {CONTENT: BASIC_CONTENT_MD}

    response = test_client.post(f"/blog/{bp_id}/comment", data=data)
    assert response.status_code == status.HTTP_200_OK
    assert "Comments (1)" in response.text
    assert BASIC_CONTENT_HTML in response.text


# ------------------------ update comment ------------------------
def test_guest_can_edit_their_own_comment(
    test_client: TestClient, basic_blog_post: db_models.BlogPost
):
    """Test a guest can edit their own comment."""
    bp = basic_blog_post
    post_data = {
        CHECK_ME: BLANK,
        NOT_ROBOT: TRUE,
        NAME: PERRIN,
        EMAIL: PERRIN_EMAIL,
        CONTENT: BASIC_CONTENT_MD,
    }

    post_response = test_client.post(f"/blog/{bp.id}/comment", data=post_data)
    assert post_response.status_code == status.HTTP_200_OK
    assert BASIC_CONTENT_HTML in post_response.text

    match = re.search(r"/blog/comment/(\d+)/edit", post_response.text)
    assert match
    comment_id = match[1]

    patch_data = {CONTENT: UPDATED_CONTENT_MD}
    response = test_client.patch(f"/blog/comment/{comment_id}", data=patch_data)
    assert response.status_code == status.HTTP_200_OK
    assert UPDATED_CONTENT_HTML in response.text


@pytest.mark.usefixtures("logged_in_basic_user")
def test_basic_user_can_edit_their_own_comment(
    test_client: TestClient,
    advanced_blog_post_with_user: db_models.BlogPost,
):
    """Test a basic user can edit their own comment."""
    bp = advanced_blog_post_with_user
    bp_comment_id = bp.comments[1].id
    data = {CONTENT: UPDATED_CONTENT_MD}
    response = test_client.patch(f"/blog/comment/{bp_comment_id}", data=data)
    assert response.status_code == status.HTTP_200_OK
    assert UPDATED_CONTENT_HTML in response.text


@pytest.mark.usefixtures("logged_in_basic_user")
def test_basic_user_cannot_edit_other_users_comment(
    test_client: TestClient, advanced_blog_post_with_user: db_models.BlogPost
):
    """Test a basic user cannot edit another user's comment."""
    bp = advanced_blog_post_with_user
    comment = bp.comments[0]
    bp_comment_id = comment.id
    data = {CONTENT: UPDATED_CONTENT_MD}
    response = test_client.patch(f"/blog/comment/{bp_comment_id}", data=data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Error editing comment" in response.text
    assert comment.html_content in response.text


@pytest.mark.usefixtures("logged_in_admin_user")
def test_admin_user_cannot_edit_other_users_comment(
    test_client: TestClient, advanced_blog_post_with_user: db_models.BlogPost
):
    """Test an admin user cannot edit another user's comment."""
    bp = advanced_blog_post_with_user
    comment = bp.comments[0]
    bp_comment_id = comment.id
    data = {CONTENT: UPDATED_CONTENT_MD}
    response = test_client.patch(f"/blog/comment/{bp_comment_id}", data=data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Error editing comment" in response.text
    assert comment.html_content in response.text


@pytest.mark.usefixtures("logged_in_basic_user")
def test_edit_comment_with_no_content_fails(
    test_client: TestClient, advanced_blog_post_with_user: db_models.BlogPost
):
    """Test editing a comment with no content fails."""
    bp = advanced_blog_post_with_user
    bp_comment_id = bp.comments[1].id
    data = {CONTENT: BLANK}
    response = test_client.patch(f"/blog/comment/{bp_comment_id}", data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Error editing comment" in response.text
    assert "No content provided" in response.text


# ------------------------ delete comment ------------------------
def test_guest_can_delete_their_own_comment(
    test_client: TestClient, basic_blog_post: db_models.BlogPost
):
    """Test a guest can delete their own comment."""
    bp = basic_blog_post
    post_data = {
        CHECK_ME: BLANK,
        NOT_ROBOT: TRUE,
        NAME: PERRIN,
        EMAIL: PERRIN_EMAIL,
        CONTENT: BASIC_CONTENT_MD,
    }

    post_response = test_client.post(f"/blog/{bp.id}/comment", data=post_data)
    assert post_response.status_code == status.HTTP_200_OK
    assert BASIC_CONTENT_HTML in post_response.text

    match = re.search(r"/blog/comment/(\d+)/edit", post_response.text)
    assert match
    comment_id = match[1]

    response = test_client.delete(f"/blog/comment/{comment_id}")
    assert response.status_code == status.HTTP_200_OK
    assert "Comment deleted" in response.text


@pytest.mark.usefixtures("logged_in_basic_user")
def test_basic_user_can_delete_their_own_comment(
    test_client: TestClient,
    advanced_blog_post_with_user: db_models.BlogPost,
):
    """Test a basic user can delete their own comment."""
    bp = advanced_blog_post_with_user
    bp_comment_id = bp.comments[1].id
    response = test_client.delete(f"/blog/comment/{bp_comment_id}")
    assert response.status_code == status.HTTP_200_OK
    assert "Comment deleted" in response.text


@pytest.mark.usefixtures("logged_in_basic_user")
def test_basic_user_cannot_delete_other_users_comment(
    test_client: TestClient, advanced_blog_post_with_user: db_models.BlogPost
):
    """Test a basic user cannot delete another user's comment."""
    bp = advanced_blog_post_with_user
    comment = bp.comments[0]
    bp_comment_id = comment.id
    response = test_client.delete(f"/blog/comment/{bp_comment_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Error deleting comment" in response.text
    assert comment.html_content in response.text


@pytest.mark.usefixtures("logged_in_admin_user")
def test_admin_user_can_delete_other_users_comment(
    test_client: TestClient, advanced_blog_post_with_user: db_models.BlogPost
):
    """Test an admin user can delete another user's comment."""
    bp = advanced_blog_post_with_user

    comment = bp.comments[0]
    bp_comment_id = comment.id
    response = test_client.delete(f"/blog/comment/{bp_comment_id}")
    assert response.status_code == status.HTTP_200_OK
    assert "Comment deleted" in response.text

    comment = bp.comments[1]
    bp_comment_id = comment.id
    response = test_client.delete(f"/blog/comment/{bp_comment_id}")
    assert response.status_code == status.HTTP_200_OK
    assert "Comment deleted" in response.text
