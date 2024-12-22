"""test_blog_edit_non_mutating: test all blog edit endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models


@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:
    """Clean the database after the module."""


# ------------------------- GET BP ------------------------
def test_get_edit_blog_post_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    response = test_client.get("/blog/1/edit", follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.get("/blog/1/edit")
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_edit_blog_post_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the edit blog post page."""
    response = test_client.get("/blog/1/edit")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_edit_blog_post_as_admin_succeeds(
    test_client: TestClient,
    basic_blog_post_module: db_models.BlogPost,
):
    """Test that an admin user can access the edit blog post page."""
    bp = basic_blog_post_module
    response = test_client.get(f"/blog/{bp.id}/edit")
    assert response.status_code == status.HTTP_200_OK
    assert "Edit Blog Post" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_edit_missing_blog_post_fails(test_client: TestClient):
    """Test that an admin user can access the edit blog post page."""
    response = test_client.get("/blog/999/edit")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "404 Error" in response.text
    assert "Blog post not found" in response.text


# ----------------------- Live-edit BP ---------------------
LIVE_EDIT_ENDPOINT = "/blog/live-edit"

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
TITLE_VAL = "some title"
TAGS_VAL = "tag1, tag2"
DESCRIPTION_MD = "some description"
CONTENT_MD = "some content"

# Others
DESCRIPTION_HTML = "<p>some description</p>"
CONTENT_HTML = "<p>some content</p>"

DEFAULT_DATA = {
    IS_NEW: FALSE,
    TITLE: TITLE_VAL,
    TAGS: TAGS_VAL,
    CAN_COMMENT: TRUE,
    IS_PUBLISHED: TRUE,
    DESCRIPTION: DESCRIPTION_MD,
    CONTENT: CONTENT_MD,
    THUMBNAIL_URL: BLANK,
}


def test_live_edit_blog_post_as_guest_fails(test_client: TestClient):
    """Test that a guest cannot live edit a blog post."""
    response = test_client.post(LIVE_EDIT_ENDPOINT, data=DEFAULT_DATA, allow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.post(LIVE_EDIT_ENDPOINT, data=DEFAULT_DATA)
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_live_edit_blog_post_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot live edit a blog post."""
    response = test_client.post(LIVE_EDIT_ENDPOINT, data=DEFAULT_DATA)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_live_edit_with_admin_succeeds(test_client: TestClient):
    """Test that an admin user can live-edit a blog post."""
    response = test_client.post(LIVE_EDIT_ENDPOINT, data=DEFAULT_DATA)
    assert response.status_code == status.HTTP_200_OK
    assert TITLE_VAL in response.text
    assert CONTENT_HTML in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_live_edit_invalid_form_fails(test_client: TestClient):
    """Test that an admin user cannot live-edit a blog post with invalid form data."""
    data = DEFAULT_DATA.copy()
    data[TITLE] = BLANK
    data[CONTENT] = BLANK
    response = test_client.post(LIVE_EDIT_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid form data." in response.text
