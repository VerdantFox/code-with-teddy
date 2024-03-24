"""test_blog_like: Test blog like functionality."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests.functional_tests.html_tests.conftest import StrToSoup


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""


# ---------------------------------- GET -------------------------------------
def test_post_toggle_like_on_and_off(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost, str_to_soup: StrToSoup
):
    """Test that a user can toggle a like on and off.

    Note that liked status is completely cookie based and does not depend on a user being logged in.
    """
    # Start with no likes, liking the post should increase the likes by 1.
    assert_on_likes(
        test_client=test_client,
        basic_blog_post_module=basic_blog_post_module,
        str_to_soup=str_to_soup,
        expected_likes=1,
    )

    # Liking the post again should decrement the likes by 1.
    assert_on_likes(
        test_client=test_client,
        basic_blog_post_module=basic_blog_post_module,
        str_to_soup=str_to_soup,
        expected_likes=0,
    )


def assert_on_likes(
    test_client: TestClient,
    basic_blog_post_module: db_models.BlogPost,
    str_to_soup: StrToSoup,
    expected_likes: int,
) -> None:
    """Assert that the number of likes is as expected."""
    response = test_client.post(f"/blog/{basic_blog_post_module.id}/like")
    assert response.status_code == status.HTTP_200_OK
    soup = str_to_soup(response.text)
    likes = soup.find(id="post-likes-count")
    assert likes
    assert int(likes.text) == expected_likes
