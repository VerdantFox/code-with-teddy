"""test_blog_get_post: Test the GET blog post page."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""


def test_get_basic_blog_post_succeeds(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post."""
    bp = basic_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    strings_to_find: tuple[str, ...] = (
        "<span>Sign In</span>",  # no user logged in
        bp.title,
        str(bp.views),
        str(bp.likes),
    )
    for string in strings_to_find:
        assert string in response.text


def test_get_blog_post_with_all_features_succeeds(
    test_client: TestClient, advanced_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post."""
    bp = advanced_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    strings_to_find: tuple[str, ...] = (
        "<span>Sign In</span>",  # no user logged in
        bp.title,
        "python",  # tag (lazy loads)
        "test",  # tag (lazy loads)
        str(bp.views),
        str(bp.likes),
        "Guest 1",  # first comment author
        "Some comment",  # first comment content
    )
    for string in strings_to_find:
        assert string in response.text


def test_get_unpublished_blog_post_as_guest_fails(
    test_client: TestClient, unpublished_blog_post_module: db_models.BlogPost
):
    """Test getting an unpublished blog post."""
    bp = unpublished_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "404 Error" in response.text
    assert "Blog post not found" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_unpublished_blog_post_as_user_fails(
    test_client: TestClient,
    unpublished_blog_post_module: db_models.BlogPost,
):
    """Test getting an unpublished blog post."""
    bp = unpublished_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "404 Error" in response.text
    assert "Blog post not found" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_unpublished_blog_post_as_admin_succeeds(
    test_client: TestClient, unpublished_blog_post_module: db_models.BlogPost
):
    """Test getting an unpublished blog post."""
    bp = unpublished_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert bp.title in response.text


def test_get_comments_disabled_blog_post_no_comment_option_as_guest(
    test_client: TestClient, blog_post_cannot_comment_module: db_models.BlogPost
):
    """Test getting a blog post with comments disabled."""
    bp = blog_post_cannot_comment_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert bp.title in response.text
    assert "Commenting has been disabled for this blog post..." in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_comments_disabled_blog_post_no_comment_option_as_user(
    test_client: TestClient, blog_post_cannot_comment_module: db_models.BlogPost
):
    """Test getting a blog post with comments disabled."""
    bp = blog_post_cannot_comment_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert bp.title in response.text
    assert "Welcome" in response.text
    assert "Commenting has been disabled for this blog post..." in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_comments_disabled_blog_post_no_comment_option_as_admin(
    test_client: TestClient, blog_post_cannot_comment_module: db_models.BlogPost
):
    """Test getting a blog post with comments disabled."""
    bp = blog_post_cannot_comment_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert bp.title in response.text
    assert "Submit a comment" in response.text
