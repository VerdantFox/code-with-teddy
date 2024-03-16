"""test_blog: Test the blog page."""

from fastapi import status
from fastapi.testclient import TestClient

PROJECTS_ENDPOINT = "/projects"


def test_get_blog_list_no_bps_succeeds(test_client: TestClient):
    """Test that the GET blog list page succeeds when no blog posts exist."""
    response = test_client.get("/blog")
    assert response.status_code == status.HTTP_200_OK
    title = "Code Chronicles"
    assert title in response.text
