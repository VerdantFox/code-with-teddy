"""test_blog_create: Test cases for creating blog posts."""

import re

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.functional_tests import BASE_URL

ENDPOINT = "/blog/create"


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""


# ---------------------------------- GET -------------------------------------
def test_get_create_blog_post_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    response = test_client.get(ENDPOINT, follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.get(ENDPOINT)
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_create_blog_post_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the create blog post page."""
    response = test_client.get(ENDPOINT)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_create_blog_post_as_admin_succeeds(test_client: TestClient):
    """Test that an admin user can access the create blog post page."""
    response = test_client.get(ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert "Create Blog Post" in response.text


# ---------------------------------- POST ------------------------------------
@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_succeeds(test_client: TestClient):
    """Test that an admin user can create a blog post."""
    title = "Test Title"
    description = "Test Description"
    content = "Test Content"
    tags = ["tag1", "tag2"]
    data = {
        "is_new": "true",
        "title": title,
        "tags": ", ".join(tags),
        "can_comment": "true",
        "is_published": "true",
        "description": description,
        "content": content,
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_200_OK
    assert re.match(rf"{BASE_URL}/blog/\d+/edit", str(response.url))
    expected_strings = (
        title,
        description,
        content,
        *tags,
    )
    for string in expected_strings:
        assert string in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_with_form_errors_fails(test_client: TestClient):
    """Test that an admin user cannot create a blog post with form errors."""
    data = {
        "is_new": "true",
        "title": "",
        "can_comment": "true",
        "is_published": "true",
        "description": "",
        "content": "some content",
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    expected_strings = (
        "Create New Blog Post",
        "Field must be at least 1 character long.",
        "some content",
    )
    for string in expected_strings:
        assert string in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_with_duplicate_post_title_fails(test_client: TestClient):
    """Test that an admin user cannot create a blog post with a duplicate title."""
    title = "Test Title"
    description = "Test Description"
    content = "Test Content"
    data = {
        "is_new": "true",
        "title": title,
        "can_comment": "true",
        "is_published": "true",
        "description": description,
        "content": content,
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_200_OK
    assert re.match(rf"{BASE_URL}/blog/\d+/edit", str(response.url))
    expected_strings: tuple[str, ...] = (
        title,
        description,
        content,
    )
    for string in expected_strings:
        assert string in response.text

    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    expected_strings = (
        "Create New Blog Post",
        "Error saving blog post",
        title,
        description,
        content,
    )
    for string in expected_strings:
        assert string in response.text
