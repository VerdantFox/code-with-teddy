"""test_landing: Test the landing about page."""

from fastapi import status
from fastapi.testclient import TestClient

LANDING_ENDPOINT = "/"


def test_get_about_succeeds(test_client: TestClient):
    """Test that the landing about page succeeds."""
    response = test_client.get(LANDING_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    title = "Web Alchemist & Python Craftsman"
    assert title in response.text


def test_missing_page_fails(test_client: TestClient):
    """Test that a missing page fails."""
    response = test_client.get("/missing")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "404 Error" in response.text
    assert "Page not found." in response.text
