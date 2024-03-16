"""test_projects: Test the projects page."""

from fastapi import status
from fastapi.testclient import TestClient

PROJECTS_ENDPOINT = "/projects"


def test_get_projects_succeeds(test_client: TestClient):
    """Test that the landing about page succeeds."""
    response = test_client.get(PROJECTS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    title = "Tech Playground"
    assert title in response.text
