"""test_main: Test the GET pages on the main site."""

from fastapi import status
from fastapi.testclient import TestClient

from tests import TestCase


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
]


@GetTestCase.parametrize(GET_TEST_CASES)
def test_get_page_succeeds(test_client: TestClient, test_case: GetTestCase):
    """Test that various GET pages succeed."""
    response = test_client.get(test_case.endpoint)
    assert response.status_code == test_case.expected_status
    assert test_case.expected_text in response.text
