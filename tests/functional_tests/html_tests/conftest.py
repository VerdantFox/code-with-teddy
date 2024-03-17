"""conftest: setup file for the functional html tests."""

from collections.abc import AsyncGenerator, Callable

import httpx
import pytest
from bs4 import BeautifulSoup
from fastapi import status
from fastapi.testclient import TestClient

from app import PROJECT_ROOT
from app.datastore import db_models

ADMIN_COOKIE: dict[str, str] = {}
BASIC_COOKIE: dict[str, str] = {}
StrToSoup = Callable[[str], BeautifulSoup]


@pytest.fixture(scope="session")
def html_to_file() -> Callable[[httpx.Response, str | None], None]:  # pragma: no cover
    """Write the html response to a file."""

    def _html_to_file(response: httpx.Response, filename: str | None = None) -> None:
        """Write the html response to a file."""
        if filename is None:
            filename = "html_response.html"
        path = PROJECT_ROOT / filename
        path.write_text(response.text)

    return _html_to_file


@pytest.fixture(scope="session")
def str_to_soup() -> StrToSoup:  # pragma: no cover
    """Convert a string to a BeautifulSoup object."""

    def _string_to_soup(html_string: str) -> BeautifulSoup:
        """Convert a string to a BeautifulSoup object."""
        return BeautifulSoup(html_string, "html.parser")

    return _string_to_soup


@pytest.fixture()
async def logged_in_basic_user(
    test_client: TestClient,
    basic_user: db_models.User,
) -> AsyncGenerator[db_models.User, None]:
    """Log in and return the basic user."""
    yield await set_basic_user_login_cookie(test_client, basic_user)
    test_client.cookies.clear()


@pytest.fixture()
async def logged_in_basic_user_module(
    test_client: TestClient,
    basic_user_module: db_models.User,
) -> AsyncGenerator[db_models.User, None]:
    """Log in and return the module-scoped basic user."""
    yield await set_basic_user_login_cookie(test_client, basic_user_module)
    test_client.cookies.clear()


async def set_basic_user_login_cookie(
    test_client: TestClient,
    user: db_models.User,
) -> db_models.User:
    """Log in and return the user."""
    if BASIC_COOKIE:
        test_client.cookies.update(BASIC_COOKIE)
    else:
        response = log_in_user(test_client, user)
        BASIC_COOKIE.update(dict(response.cookies))
    return user


@pytest.fixture()
async def logged_in_admin_user(
    test_client: TestClient,
    admin_user: db_models.User,
) -> AsyncGenerator[db_models.User, None]:
    """Log in and return the admin user."""
    yield await set_admin_user_login_cookie(test_client, admin_user)
    test_client.cookies.clear()


@pytest.fixture()
async def logged_in_admin_user_module(
    test_client: TestClient,
    admin_user_module: db_models.User,
) -> AsyncGenerator[db_models.User, None]:
    """Log in and return the module-scoped admin user."""
    yield await set_admin_user_login_cookie(test_client, admin_user_module)
    test_client.cookies.clear()


async def set_admin_user_login_cookie(
    test_client: TestClient,
    user: db_models.User,
) -> db_models.User:
    """Log in and return the user."""
    if ADMIN_COOKIE:
        test_client.cookies.update(ADMIN_COOKIE)
    else:
        response = log_in_user(test_client, user)
        ADMIN_COOKIE.update(dict(response.cookies))
    return user


def log_in_user(
    test_client: TestClient,
    user: db_models.User,
) -> httpx.Response:
    """Log in a user and return the response."""
    login_data: dict[str, str] = {
        "username_or_email": user.username,
        "password": "password",
    }
    response = test_client.post("/auth/token", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.cookies
    assert "access_token" in response.json()
    return response
