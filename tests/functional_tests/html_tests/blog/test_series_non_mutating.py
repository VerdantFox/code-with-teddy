"""test_series_non_mutating: Test the blog post series non-mutating endpoints."""

from enum import Enum

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import TestCase
from tests.functional_tests.html_tests.conftest import StrToSoup

BLOG_ENDPOINT = "/blog"
BLOG_SERIES_ENDPOINT = "/blog/series"
LIST_BLOG_SERIES_TITLE = "Manage Series"


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:
    """Clean the database after the module."""


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------
@pytest.mark.usefixtures("empty_series_module")
def test_get_blog_series_list_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    response = test_client.get(BLOG_SERIES_ENDPOINT, follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.get(BLOG_SERIES_ENDPOINT)
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_blog_series_list_page_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the blog series list page."""
    response = test_client.get(BLOG_SERIES_ENDPOINT)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_blog_series_list_page_as_admin_succeeds(
    test_client: TestClient,
    empty_series_module: db_models.BlogPostSeries,
    series_with_posts_module: db_models.BlogPostSeries,
    str_to_soup: StrToSoup,
):
    """Test that an admin user can access the blog series list page."""
    response = test_client.get(BLOG_SERIES_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert LIST_BLOG_SERIES_TITLE in response.text
    soup = str_to_soup(response.text)
    series_count_td_elements = soup.find_all("td", class_="series-count")
    actual_series_counts = [int(element.get_text()) for element in series_count_td_elements]
    assert len(empty_series_module.posts) in actual_series_counts
    assert len(series_with_posts_module.posts) in actual_series_counts
    assert series_with_posts_module.name in response.text


def test_get_blog_post_in_series(
    test_client: TestClient,
    series_with_posts_module: db_models.BlogPostSeries,
):  # sourcery skip: extract-duplicate-method
    """Test getting blog posts in a series."""
    # Get the first post in the series
    first_post = series_with_posts_module.posts[0]
    response = test_client.get(f"{BLOG_ENDPOINT}/{first_post.slug}")
    assert response.status_code == status.HTTP_200_OK
    for post in series_with_posts_module.posts:
        assert post.title in response.text
        assert f"/{post.slug}" in response.text

    assert "(this post)" in response.text
    assert "Up next in blog series:" in response.text

    # Get the last post in the series
    last_post = series_with_posts_module.posts[-1]
    response = test_client.get(f"{BLOG_ENDPOINT}/{last_post.slug}")
    assert response.status_code == status.HTTP_200_OK
    for post in series_with_posts_module.posts:
        assert post.title in response.text
        assert f"/{post.slug}" in response.text
    assert "(this post)" in response.text
    assert "Up next in blog series:" not in response.text


class SeriesEnum(str, Enum):
    """Enum for the series form."""

    EMPTY = "empty"
    POSTS = "posts"


class SearchTestCase(TestCase):
    """Test case for the search form."""

    search: str
    found: list[SeriesEnum]


SEARCH_CASES = [
    SearchTestCase(id="all", search="", found=[SeriesEnum.EMPTY, SeriesEnum.POSTS]),
    SearchTestCase(id="empty", search="empty", found=[SeriesEnum.EMPTY]),
    SearchTestCase(id="posts", search="posts", found=[SeriesEnum.POSTS]),
    SearchTestCase(id="posts_description", search="description", found=[SeriesEnum.POSTS]),
    SearchTestCase(id="no match", search="no match", found=[]),
]


@SearchTestCase.parametrize(SEARCH_CASES)
@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_blog_series_list_page_search(
    test_client: TestClient,
    empty_series_module: db_models.BlogPostSeries,
    series_with_posts_module: db_models.BlogPostSeries,
    test_case: SearchTestCase,
    str_to_soup: StrToSoup,
):
    """Test that an admin user can access the blog series list page."""
    response = test_client.get(BLOG_SERIES_ENDPOINT, params={"search": test_case.search})
    assert response.status_code == status.HTTP_200_OK
    assert LIST_BLOG_SERIES_TITLE in response.text
    soup = str_to_soup(response.text)
    series_count_td_elements = soup.find_all("td", class_="series-count")
    actual_series_counts = [int(element.get_text()) for element in series_count_td_elements]
    if SeriesEnum.EMPTY in test_case.found:
        assert len(empty_series_module.posts) in actual_series_counts
    else:
        assert len(empty_series_module.posts) not in actual_series_counts
    if SeriesEnum.POSTS in test_case.found:
        assert len(series_with_posts_module.posts) in actual_series_counts
        assert series_with_posts_module.name in response.text
    else:
        assert len(series_with_posts_module.posts) not in actual_series_counts
        assert series_with_posts_module.name not in response.text
