"""test_series_non_mutating: Test the blog post series mutating endpoints."""

from dataclasses import field

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import TestCase

BLOG_SERIES_ENDPOINT = "/blog/series"
LIST_BLOG_SERIES_TITLE = "Manage Series"

SIGN_IN = "Sign In</h1>"
FORBIDDEN = "403 Error"
PERMISSION = "You do not have permission to perform this action"


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module."""


@pytest.fixture(autouse=True)
async def _clean_db_fixture_function(clean_db_except_users: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each function."""


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------
def test_post_blog_series_list_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    response = test_client.post(BLOG_SERIES_ENDPOINT, follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.post(BLOG_SERIES_ENDPOINT)
    assert SIGN_IN in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_post_blog_series_list_page_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the post blog series page."""
    response = test_client.post(BLOG_SERIES_ENDPOINT)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert FORBIDDEN in response.text
    assert PERMISSION in response.text


def test_put_blog_series_list_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    put_endpoint = f"{BLOG_SERIES_ENDPOINT}/1"
    response = test_client.put(put_endpoint, follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.put(put_endpoint)
    assert SIGN_IN in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_put_blog_series_list_page_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the put blog series page."""
    put_endpoint = f"{BLOG_SERIES_ENDPOINT}/1"
    response = test_client.put(put_endpoint)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert FORBIDDEN in response.text
    assert PERMISSION in response.text


def test_delete_blog_series_list_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    delete_endpoint = f"{BLOG_SERIES_ENDPOINT}/1"
    response = test_client.delete(delete_endpoint, follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.delete(delete_endpoint)
    assert SIGN_IN in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_delete_blog_series_list_page_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the delete blog series page."""
    delete_endpoint = f"{BLOG_SERIES_ENDPOINT}/1"
    response = test_client.delete(delete_endpoint)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert FORBIDDEN in response.text
    assert PERMISSION in response.text


class PostSeriesTestCase(TestCase):
    """Test case for creating a blog series."""

    name: str
    description: str = ""
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = field(default_factory=list)
    expected_missing_strings: list[str] = field(default_factory=list)


POST_SERIES_CASES = [
    PostSeriesTestCase(
        id="name",
        name="Test Series",
        expected_strings=["Series Created!", "Test Series"],
    ),
    PostSeriesTestCase(
        id="name_description",
        name="Test Series",
        description="Test Description",
        expected_strings=["Series Created!", "Test Series", "Test Description"],
    ),
    PostSeriesTestCase(
        id="no_name",
        name="",
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["Error creating series", "Field must be at least 1 character long."],
        expected_missing_strings=["Series Created!"],
    ),
    PostSeriesTestCase(
        id="repeat_name",
        name="Empty series",
        expected_status_code=status.HTTP_400_BAD_REQUEST,
        expected_strings=["Error creating series", "Name already exists."],
        expected_missing_strings=["Series Created!"],
    ),
]


@PostSeriesTestCase.parametrize(POST_SERIES_CASES)
@pytest.mark.usefixtures("logged_in_admin_user_module", "empty_series")
def test_post_create_blog_series_as_admin(test_client: TestClient, test_case: PostSeriesTestCase):
    """Test creating a series as the admin user."""
    response = test_client.post(BLOG_SERIES_ENDPOINT, data=test_case.model_dump())
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    for string in test_case.expected_missing_strings:
        assert string not in response.text


class PutSeriesTestCase(TestCase):
    """Test case for updating a blog series."""

    name: str
    description: str = ""
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = field(default_factory=list)
    expected_missing_strings: list[str] = field(default_factory=list)


PUT_SERIES_CASES = [
    PutSeriesTestCase(
        id="name",
        name="Test Series",
        expected_strings=["Series Updated!", "Test Series"],
    ),
    PutSeriesTestCase(
        id="name_description",
        name="Test Series",
        description="Test Description",
        expected_strings=["Series Updated!", "Test Series", "Test Description"],
    ),
    PutSeriesTestCase(
        id="no_name",
        name="",
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["Error updating series", "Field must be at least 1 character long."],
        expected_missing_strings=["Series Updated!"],
    ),
    PutSeriesTestCase(
        id="repeat_name",
        name="Empty series 2",
        expected_status_code=status.HTTP_400_BAD_REQUEST,
        expected_strings=["Error updating series", "Name already exists."],
        expected_missing_strings=["Series Updated!"],
    ),
]


@PutSeriesTestCase.parametrize(PUT_SERIES_CASES)
@pytest.mark.usefixtures("logged_in_admin_user_module", "empty_series_2")
def test_put_update_blog_series_as_admin(
    test_client: TestClient, empty_series: db_models.BlogPostSeries, test_case: PutSeriesTestCase
):
    """Test creating a series as the admin user."""
    endpoint = f"{BLOG_SERIES_ENDPOINT}/{empty_series.id}"
    response = test_client.put(endpoint, data=test_case.model_dump())
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    for string in test_case.expected_missing_strings:
        assert string not in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_delete_series(
    test_client: TestClient,
    series_with_post: db_models.BlogPostSeries,
    basic_blog_post: db_models.BlogPost,
):
    """Test deleting a blog series."""
    # Check that the series exists
    response = test_client.get(BLOG_SERIES_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert LIST_BLOG_SERIES_TITLE in response.text

    # Check that the blog post links to the series
    response = test_client.get(f"/blog/{basic_blog_post.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert "Posts in Series" in response.text

    # Delete the series
    endpoint = f"{BLOG_SERIES_ENDPOINT}/{series_with_post.id}"
    response = test_client.delete(endpoint)
    assert response.status_code == status.HTTP_200_OK
    assert "Series Deleted!" in response.text

    # Check that the series is deleted
    response = test_client.get(BLOG_SERIES_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert LIST_BLOG_SERIES_TITLE in response.text
    assert series_with_post.name not in response.text

    # Check that the blog post does not have a series
    response = test_client.get(f"/blog/{basic_blog_post.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert series_with_post.name not in response.text
