"""test_blog_get_post: Test the GET blog post page."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models

BP_NOT_FOUND = "Blog post not found"
ERROR_404 = "404 Error"


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module."""


def test_get_basic_blog_post_succeeds(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post as a guest."""
    bp = basic_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    expected_strings = (
        "<span>Sign In</span>",  # no user logged in
        bp.title,
        str(bp.views),
        str(bp.likes),
    )
    for string in expected_strings:
        assert string in response.text
    unexpected_strings = (
        "<span>Sign Out</span>",
        "User Settings",
        "Edit Blog Post",
        "Create Blog Post",
    )
    for string in unexpected_strings:
        assert string not in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_basic_blog_post_succeeds_signed_in_succeeds(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post as a signed in basic user."""
    bp = basic_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    expected_strings = (
        "Welcome",
        "<span>Sign Out</span>",
        "User Settings",
        bp.title,
        str(bp.views),
        str(bp.likes),
    )
    for string in expected_strings:
        assert string in response.text
    unexpected_strings = (
        "<span>Sign In</span>",
        "Edit Blog Post",
        "Create Blog Post",
    )
    for string in unexpected_strings:
        assert string not in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_basic_blog_post_succeeds_signed_in_admin_succeeds(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post as a signed in admin."""
    bp = basic_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    expected_strings = (
        "Welcome",
        "<span>Sign Out</span>",
        "User Settings",
        bp.title,
        str(bp.views),
        str(bp.likes),
        "Edit Blog Post",
        "Create Blog Post",
    )
    for string in expected_strings:
        assert string in response.text
    unexpected_strings = ("<span>Sign In</span>",)
    for string in unexpected_strings:
        assert string not in response.text


def test_get_blog_post_with_all_features_succeeds(
    test_client: TestClient, advanced_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post."""
    bp = advanced_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_200_OK
    expected_strings = (
        "<span>Sign In</span>",  # no user logged in
        bp.title,
        "python",  # tag (lazy loads)
        "test",  # tag (lazy loads)
        str(bp.views),
        str(bp.likes),
        "Guest 1",  # first comment author
        "Some comment",  # first comment content
    )
    for string in expected_strings:
        assert string in response.text


def test_get_unpublished_blog_post_as_guest_fails(
    test_client: TestClient, unpublished_blog_post_module: db_models.BlogPost
):
    """Test getting an unpublished blog post."""
    bp = unpublished_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert ERROR_404 in response.text
    assert BP_NOT_FOUND in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_unpublished_blog_post_as_user_fails(
    test_client: TestClient,
    unpublished_blog_post_module: db_models.BlogPost,
):
    """Test getting an unpublished blog post."""
    bp = unpublished_blog_post_module
    response = test_client.get(f"/blog/{bp.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert ERROR_404 in response.text
    assert BP_NOT_FOUND in response.text


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
    expected_strings: list[str] = [
        bp.title,
        "Welcome",
        "Commenting has been disabled for this blog post...",
    ]
    for string in expected_strings:
        assert string in response.text


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


def test_get_missing_blogpost_fails(test_client: TestClient):
    """Test getting a missing blog post."""
    response = test_client.get("/blog/missing-blog-post")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert ERROR_404 in response.text
    assert BP_NOT_FOUND in response.text


def test_get_blog_post_with_old_slug_redirects(
    test_client: TestClient, advanced_blog_post_module: db_models.BlogPost
):
    """Test getting a blog post with an old slug."""
    bp = advanced_blog_post_module
    old_slug = bp.old_slugs[0]
    response = test_client.get(f"/blog/{old_slug.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert bp.title in response.text
