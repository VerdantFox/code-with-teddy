"""test_main: Test the GET pages on the main site."""

from dataclasses import dataclass

import pytest
from fastapi import status
from fastapi.testclient import TestClient

pytestmark = pytest.mark.anyio


@dataclass
class GetTestCase:
    """Test cases for the GET pages."""

    test_id: str
    endpoint: str
    expected_text: str
    expected_status: int = status.HTTP_200_OK


GET_TEST_CASES = [
    GetTestCase(
        test_id="landing",
        endpoint="/",
        expected_text="Web Alchemist & Python Craftsman",
    ),
    GetTestCase(
        test_id="projects",
        endpoint="/projects",
        expected_text="Tech Playground",
    ),
    GetTestCase(
        test_id="experience",
        endpoint="/experience",
        expected_text="Professional Journey",
    ),
    GetTestCase(
        test_id="not_found",
        endpoint="/missing",
        expected_text="404 Error",
        expected_status=status.HTTP_404_NOT_FOUND,
    ),
]


@pytest.mark.parametrize(
    "test_case",
    [pytest.param(test_case, id=test_case.test_id) for test_case in GET_TEST_CASES],
)
async def test_get_page_succeeds(test_client: TestClient, test_case: GetTestCase):
    """Test that various GET pages succeed."""
    response = test_client.get(test_case.endpoint)
    assert response.status_code == test_case.expected_status
    assert test_case.expected_text in response.text
