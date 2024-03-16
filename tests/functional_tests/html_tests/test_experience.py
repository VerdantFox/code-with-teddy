"""test_experience: Test the experience page."""

from fastapi import status
from fastapi.testclient import TestClient

EXPERIENCE_ENDPOINT = "/experience"


def test_get_experience_succeeds(test_client: TestClient):
    """Test that the landing about page succeeds."""
    response = test_client.get(EXPERIENCE_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    title = "Experience"
    assert title in response.text
