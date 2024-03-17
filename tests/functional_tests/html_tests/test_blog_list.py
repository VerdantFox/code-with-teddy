"""test_blog: Test the blog page."""

from dataclasses import dataclass, field

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests.functional_tests.html_tests.conftest import StrToSoup

BLOG_ENDPOINT = "/blog"
LIST_POSTS_TITLE = "Code Chronicles"


@pytest.fixture(scope="module", autouse=True)
async def _clean_db_fixture(clean_db_module: None) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module."""


@pytest.fixture(name="blog_posts")
def blog_posts_fixture(
    several_blog_posts_module: list[db_models.BlogPost],
) -> list[db_models.BlogPost]:
    """Return several blog posts."""
    return several_blog_posts_module.copy()


def test_get_blog_list_guest_succeeds(
    test_client: TestClient, blog_posts: list[db_models.BlogPost]
):
    """Test that the GET blog list page succeeds."""
    response = test_client.get(BLOG_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert LIST_POSTS_TITLE in response.text
    unpublished_blog_post = blog_posts.pop(1)
    assert unpublished_blog_post.title not in response.text
    assert "Sign In" in response.text
    for blog_post in blog_posts:
        assert blog_post.title in response.text


def test_get_blog_list_basic_user_succeeds(
    test_client: TestClient,
    blog_posts: list[db_models.BlogPost],
    logged_in_basic_user_module: db_models.User,
    str_to_soup: StrToSoup,
):
    """Test that the GET blog list page succeeds."""
    response = test_client.get(BLOG_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert LIST_POSTS_TITLE in response.text

    unpublished_blog_post = blog_posts.pop(1)

    assert unpublished_blog_post.title not in response.text
    assert "Welcome" in response.text
    assert logged_in_basic_user_module.username in response.text
    for blog_post in blog_posts:
        assert blog_post.title in response.text

    soup = str_to_soup(response.text)
    total_results = int(soup.find(id="desktop-total-results").text)
    assert total_results == len(blog_posts)


def test_get_blog_list_admin_user_succeeds(
    test_client: TestClient,
    blog_posts: list[db_models.BlogPost],
    logged_in_admin_user_module: db_models.User,
    str_to_soup: StrToSoup,
):
    """Test that the GET blog list page succeeds."""
    response = test_client.get(BLOG_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert LIST_POSTS_TITLE in response.text

    assert "Welcome" in response.text
    assert logged_in_admin_user_module.username in response.text

    # Admin user can see all blog posts (including unpublished)
    for blog_post in blog_posts:
        assert blog_post.title in response.text

    soup = str_to_soup(response.text)
    total_results = int(soup.find(id="desktop-total-results").text)
    assert total_results == len(blog_posts)


@dataclass
class SearchTestCase:
    """Search test case."""

    test_id: str
    search: str = ""
    tags: str = ""
    results_per_page: int = 0
    page: int = 1
    order_by: str = ""
    asc: str = ""
    expected_min_result: int = 1
    expected_max_result: int = 3
    expected_total_results: int = 3
    expected_bp_titles: list[int] = field(default_factory=lambda: [4, 3, 1])


SEARCH_PARAMS = (
    "search",
    "tags",
    "results_per_page",
    "page",
    "order_by",
    "asc",
)


SEARCH_TEST_CASES = [
    SearchTestCase(
        test_id="search_all",
    ),
    SearchTestCase(
        test_id="search_content_all",
        search="test blog post",
    ),
    SearchTestCase(
        test_id="search_title",
        search="1",
        expected_bp_titles=[1],
        expected_max_result=1,
        expected_total_results=1,
    ),
    SearchTestCase(
        test_id="search_tags",
        tags="foo_4",
        expected_bp_titles=[4, 3],
        expected_max_result=2,
        expected_total_results=2,
    ),
    SearchTestCase(
        test_id="two_per_page_page_1",
        results_per_page=2,
        expected_max_result=2,
        expected_total_results=3,
        expected_bp_titles=[4, 3],
    ),
    SearchTestCase(
        test_id="two_per_page_page_2",
        results_per_page=2,
        page=2,
        expected_min_result=3,
        expected_max_result=3,
        expected_total_results=3,
        expected_bp_titles=[1],
    ),
    SearchTestCase(
        test_id="order_by_title_asc",
        order_by="title",
        asc="true",
        expected_bp_titles=[1, 3, 4],
    ),
    SearchTestCase(
        test_id="order_by_title_desc",
        order_by="title",
        asc="false",
        expected_bp_titles=[4, 3, 1],
    ),
]


@pytest.mark.usefixtures("blog_posts")
@pytest.mark.parametrize(
    "test_case",
    [pytest.param(test_case, id=test_case.test_id) for test_case in SEARCH_TEST_CASES],
)
def test_search_blog_posts(
    test_client: TestClient, test_case: SearchTestCase, str_to_soup: StrToSoup
):
    """Test searching blog posts."""
    search_params = {}
    for param in SEARCH_PARAMS:
        if value := getattr(test_case, param):
            search_params[param] = value
    response = test_client.get(BLOG_ENDPOINT, params=search_params)
    assert response.status_code == status.HTTP_200_OK

    soup = str_to_soup(response.text)
    total_results = int(soup.find(id="desktop-total-results").text)
    assert total_results == test_case.expected_total_results

    titles_from_html = [title.text for title in soup.find_all(class_="bp-title")]
    expected_titles = [f"basic_{i}" for i in test_case.expected_bp_titles]
    assert titles_from_html == expected_titles
