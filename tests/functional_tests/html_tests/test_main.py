"""test_main: Test the GET pages on the main site."""

from xml.etree import ElementTree

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests import TestCase


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module completes."""


class GetTestCase(TestCase):
    """Test cases for the GET pages."""

    endpoint: str
    expected_text: str
    expected_status: int = status.HTTP_200_OK


GET_TEST_CASES = [
    GetTestCase(
        id="landing",
        endpoint="/",
        expected_text="Web Alchemist & Python Craftsman",
    ),
    GetTestCase(
        id="projects",
        endpoint="/projects",
        expected_text="Tech Playground",
    ),
    GetTestCase(
        id="experience",
        endpoint="/experience",
        expected_text="Professional Journey",
    ),
    GetTestCase(
        id="not_found",
        endpoint="/missing",
        expected_text="404 Error",
        expected_status=status.HTTP_404_NOT_FOUND,
    ),
    GetTestCase(
        id="twisted_towers",
        endpoint="/twisted-towers",
        expected_text="Twisted Towers",
    ),
    GetTestCase(
        id="moth_hunt",
        endpoint="/moth-hunt",
        expected_text="Moth Hunt",
    ),
    GetTestCase(
        id="file_renamer",
        endpoint="/file-renamer",
        expected_text="File Renamer",
    ),
]


@GetTestCase.parametrize(GET_TEST_CASES)
def test_get_page_succeeds(test_client: TestClient, test_case: GetTestCase):
    """Test that various GET pages succeed."""
    response = test_client.get(test_case.endpoint)
    assert response.status_code == test_case.expected_status
    assert test_case.expected_text in response.text


@pytest.mark.usefixtures("basic_blog_post_module")
def test_get_sitemap_xml_succeeds(test_client: TestClient):
    """Test that the sitemap.xml page succeeds and parses as XML."""
    response = test_client.get("/sitemap.xml")
    assert response.status_code == status.HTTP_200_OK

    # Should parse as XML
    ElementTree.fromstring(response.text)  # noqa: S314 (xml-vulnerability)
    assert "urlset" in response.text
    assert "<loc>https://www.code-with-teddy.com</loc>" in response.text
    assert "<loc>https://www.code-with-teddy.com/blog/module-blog-post</loc>" in response.text
