"""test_blog_updates: Test blog updates functionality."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests.functional_tests.html_tests.conftest import StrToSoup


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""


# ---------------------------------- GET -------------------------------------
def test_post_toggle_like_on_and_off(
    test_client: TestClient, basic_blog_post: db_models.BlogPost, str_to_soup: StrToSoup
):
    """Test that a user can toggle a like on and off.

    Note that liked status is completely cookie based and does not depend on a user being logged in.
    """
    # Start with no likes, liking the post should increase the likes by 1.
    assert_on_likes(
        test_client=test_client,
        bp=basic_blog_post,
        str_to_soup=str_to_soup,
        expected_likes=1,
    )

    # Liking the post again should decrement the likes by 1.
    assert_on_likes(
        test_client=test_client,
        bp=basic_blog_post,
        str_to_soup=str_to_soup,
        expected_likes=0,
    )


def assert_on_likes(
    test_client: TestClient,
    bp: db_models.BlogPost,
    str_to_soup: StrToSoup,
    expected_likes: int,
) -> None:
    """Assert that the number of likes is as expected."""
    response = test_client.post(f"/blog/{bp.id}/like")
    assert response.status_code == status.HTTP_200_OK
    soup = str_to_soup(response.text)
    likes = soup.find(id="post-likes-count")
    assert likes
    assert int(likes.text) == expected_likes


def test_view_blog_post(test_client: TestClient, basic_blog_post: db_models.BlogPost):
    # sourcery skip: extract-duplicate-method
    """Test the view_blog_post route."""
    # First view updates the views by 1.
    response = test_client.get(f"/blog/{basic_blog_post.id}/view")
    assert response.status_code == status.HTTP_200_OK
    assert response.text == "1"

    # Second view does not update the views since the post has already been viewed.
    response = test_client.get(f"/blog/{basic_blog_post.id}/view")
    assert response.status_code == status.HTTP_200_OK
    assert response.text == "1"
