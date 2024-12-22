"""test_users_non_mutating: test non-mutating API users routes."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models

USERS_ENDPOINT = "/api/v1/users"
GET_CURRENT_USER_ENDPOINT = f"{USERS_ENDPOINT}/current-user"


@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:
    """Clean the database after the module."""


@pytest.mark.usefixtures("basic_user_module", "admin_user_module")
def test_get_users_as_guest(test_client: TestClient) -> None:
    """Should return a list of users as a guest."""
    response = test_client.get(USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_users_as_basic_user_unauthorized(test_client: TestClient) -> None:
    """Should return an unauthorized error as a user."""
    auth_header = test_client.headers.get("Authorization")
    test_client.headers["Authorization"] = auth_header[:-1]
    response = test_client.get(USERS_ENDPOINT)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Unable to validate user from JWT token"}


@pytest.mark.usefixtures("admin_user_module")
def test_get_users_as_basic_user(
    logged_in_basic_user_module: db_models.User, test_client: TestClient
) -> None:
    """Should return a list of users as a user."""
    response = test_client.get(USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    user = body[0]
    assert user["id"] == logged_in_basic_user_module.id


@pytest.mark.usefixtures("logged_in_admin_user_module", "basic_user_module")
def test_get_users_as_admin(
    test_client: TestClient,
) -> None:
    """Should return a list of users as an admin."""
    response = test_client.get(USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2


def test_get_current_user_as_guest(test_client: TestClient) -> None:
    """Should return an unauthenticated user as a guest."""
    response = test_client.get(GET_CURRENT_USER_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": -1,
        "username": "unauthenticated_user",
        "email": "unauthenticated@email.com",
        "full_name": "Unauthenticated User",
        "timezone": "UTC",
        "avatar_location": None,
        "role": "unauthenticated",
        "is_active": False,
    }


def test_get_current_user_as_basic_user(
    logged_in_basic_user_module: db_models.User, test_client: TestClient
) -> None:
    """Should return the basic user as a user."""
    response = test_client.get(GET_CURRENT_USER_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == logged_in_basic_user_module.id


def test_get_user_as_guest(test_client: TestClient) -> None:
    """Should return an unauthenticated user as a guest."""
    response = test_client.get(f"{USERS_ENDPOINT}/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_other_user_as_basic_user(
    test_client: TestClient, admin_user_module: db_models.User
) -> None:
    """Should not find the other user as a user."""
    response = test_client.get(f"{USERS_ENDPOINT}/{admin_user_module.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}


def test_get_self_as_basic_user(
    logged_in_basic_user_module: db_models.User, test_client: TestClient
) -> None:
    """Should return the basic user as a user."""
    response = test_client.get(f"{USERS_ENDPOINT}/{logged_in_basic_user_module.id}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == logged_in_basic_user_module.id


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_user_as_admin(basic_user_module: db_models.User, test_client: TestClient) -> None:
    """Should return another user as an admin."""
    response = test_client.get(f"{USERS_ENDPOINT}/{basic_user_module.id}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == basic_user_module.id
