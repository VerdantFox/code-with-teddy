"""test_auth: Test the authentication API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests import TestCase
from tests.data import models as test_models

TOKEN_URL = "api/v1/auth/token"


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:
    """Clean the database after the module."""


class GetAccessTokenTestCase(TestCase):
    """TestCase for getting an access token."""

    data: dict[str, str]
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012 (mutable default)
    expected_json: dict[str, str] = {}  # noqa: RUF012 (mutable default)


ACCESS_TOKEN = "access_token"

GET_ACCESS_TOKEN_TEST_CASES = [
    GetAccessTokenTestCase(
        id="success_with_username",
        data={
            "username": test_models.BASIC_USER[test_models.UserModelKeys.USERNAME],
            "password": test_models.PASSWORD_VAL,
        },
        expected_strings=[ACCESS_TOKEN],
    ),
    GetAccessTokenTestCase(
        id="success_with_email",
        data={
            "username": test_models.BASIC_USER[test_models.UserModelKeys.EMAIL],
            "password": test_models.PASSWORD_VAL,
        },
        expected_strings=[ACCESS_TOKEN],
    ),
    GetAccessTokenTestCase(
        id="bad_password",
        data={
            "username": test_models.BASIC_USER[test_models.UserModelKeys.EMAIL],
            "password": "bad_password",
        },
        expected_status_code=status.HTTP_401_UNAUTHORIZED,
        expected_json={"detail": "Incorrect username or password"},
    ),
    GetAccessTokenTestCase(
        id="bad_username",
        data={
            "username": "bad_username",
            "password": test_models.PASSWORD_VAL,
        },
        expected_status_code=status.HTTP_401_UNAUTHORIZED,
        expected_json={"detail": "Incorrect username or password"},
    ),
]


@GetAccessTokenTestCase.parametrize(GET_ACCESS_TOKEN_TEST_CASES)
@pytest.mark.usefixtures("basic_user_module")
def test_get_access_token_succeeds(
    test_client: TestClient,
    test_case: GetAccessTokenTestCase,
) -> None:
    """Test getting an access token."""
    response = test_client.post(TOKEN_URL, data=test_case.data)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    if test_case.expected_json:
        assert response.json() == test_case.expected_json
