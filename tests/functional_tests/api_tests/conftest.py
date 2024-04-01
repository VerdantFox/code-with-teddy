"""conftest: pytest configuration file for the api_tests directory."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import ADMIN_TOKEN, BASIC_TOKEN
from tests.data import models as test_models

TOKEN_URL = "api/v1/auth/token"


@pytest.fixture()
async def logged_in_basic_user_module(
    test_client: TestClient,
    basic_user_module: db_models.User,
) -> AsyncGenerator[db_models.User, None]:
    """Log in and return the module-scoped basic user."""
    login_headers = get_login_headers(test_client, basic_user_module)
    test_client.headers.update(login_headers)
    yield basic_user_module
    test_client.headers.clear()


@pytest.fixture()
async def logged_in_admin_user_module(
    test_client: TestClient,
    admin_user_module: db_models.User,
) -> AsyncGenerator[db_models.User, None]:
    """Log in and return the module-scoped admin user."""
    login_headers = get_login_headers(test_client, admin_user_module)
    test_client.headers.update(login_headers)
    yield admin_user_module
    test_client.headers.clear()


def get_login_headers(test_client: TestClient, user: db_models.User) -> dict[str, str]:
    # sourcery skip: dict-assign-update-to-union
    """Return the login token for the user."""
    cache: dict[str, str] = ADMIN_TOKEN if user.is_admin else BASIC_TOKEN
    if not cache:
        cache.update(post_for_token(test_client, user))
    return cache


def post_for_token(test_client: TestClient, user: db_models.User) -> dict[str, str]:
    """Post the user's credentials to the token URL and return the access token."""
    data = {"username": user.username, "password": test_models.PASSWORD_VAL}
    response = test_client.post(TOKEN_URL, data=data)
    assert response.status_code == status.HTTP_200_OK
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
