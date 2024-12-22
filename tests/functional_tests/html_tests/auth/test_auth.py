"""test_auth: tests for auth routes."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

REFRESH_TOKEN_URL = "/auth/refresh-token-cookie"


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db: None, anyio_backend: str) -> None:
    """Clean the database after each test."""


def test_refresh_access_token_as_guest(test_client: TestClient) -> None:
    """Test that a guest cannot refresh an access token."""
    response = test_client.get(REFRESH_TOKEN_URL)
    assert response.status_code == status.HTTP_200_OK
    assert response.text.strip() == ""
    assert "access_token" not in response.cookies


@pytest.mark.usefixtures("logged_in_basic_user")
def test_refresh_access_token_as_user(test_client: TestClient) -> None:
    """Test that a user can refresh an access token."""
    response = test_client.get(REFRESH_TOKEN_URL)
    assert response.status_code == status.HTTP_200_OK
    assert response.text.strip() != ""
    assert "access_token" in response.cookies


@pytest.mark.usefixtures("logged_in_basic_user")
def test_refresh_access_token_as_user_with_invalid_token(test_client: TestClient) -> None:
    """Test that a user can refresh an access token with a remaining time."""
    # replace test_client access_token cookie with an invalid token
    token = test_client.cookies["access_token"]
    invalid_token = f"{token}invalid"
    test_client.cookies.clear()
    test_client.cookies["access_token"] = invalid_token

    response = test_client.get(REFRESH_TOKEN_URL)
    assert response.status_code == status.HTTP_200_OK
    assert response.text.strip() == ""
    assert "access_token" not in response.cookies
