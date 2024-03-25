"""test_users_non_mutating: test the non-mutating user endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import TestCase
from tests.data import models as test_models


@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module."""


# ------------------------- Login ------------------------
class LoginLogoutTestCase(TestCase):
    """Test case for the login page."""

    data: dict[str, str] = {}  # noqa: RUF012
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012
    unexpected_strings: list[str] = []  # noqa: RUF012
    expected_headers: dict[str, str] = {}  # noqa: RUF012
    expect_access_token: bool = False


# Form fields
USERNAME_OR_EMAIL = "username_or_email"
PASSWORD = "password"
NEXT = "next"  # redirect_url is aliased to "next"

# Form field values
USERNAME_VAL: str = test_models.BASIC_USER[test_models.UserModelKeys.USERNAME]  # type: ignore[assignment]
EMAIL_VAL: str = test_models.BASIC_USER[test_models.UserModelKeys.EMAIL]  # type: ignore[assignment]
PASSWORD_VAL = test_models.PASSWORD_VAL
REDIRECT_URL_VAL = "/foobar"
BLANK = ""

# Headers
REDIRECT_HEADER = "hx-redirect"
SET_COOKIE_HEADER = "set-cookie"

# Others
SIGN_IN = "Sign In"

LOGIN_GET_TEST_CASES = [
    LoginLogoutTestCase(id="default", expected_strings=[SIGN_IN]),
    LoginLogoutTestCase(
        id="with_all_fields",
        data={
            USERNAME_OR_EMAIL: USERNAME_VAL,
            PASSWORD: PASSWORD_VAL,
            NEXT: REDIRECT_URL_VAL,
        },
        expected_strings=[SIGN_IN, USERNAME_VAL, REDIRECT_URL_VAL],
        unexpected_strings=[PASSWORD_VAL],
    ),
]


@pytest.mark.usefixtures("basic_user_module")
@LoginLogoutTestCase.parametrize(LOGIN_GET_TEST_CASES)
def test_login_get(test_client: TestClient, test_case: LoginLogoutTestCase):
    """Test that the login get page."""
    response = test_client.get("/login", params=test_case.data)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    for string in test_case.unexpected_strings:
        assert string not in response.text


LOGIN_POST_TEST_CASES = [
    LoginLogoutTestCase(
        id="valid_login",
        data={USERNAME_OR_EMAIL: USERNAME_VAL, PASSWORD: PASSWORD_VAL},
        expected_headers={REDIRECT_HEADER: "/"},
        expect_access_token=True,
    ),
    LoginLogoutTestCase(
        id="valid_login_redirect",
        data={USERNAME_OR_EMAIL: USERNAME_VAL, PASSWORD: PASSWORD_VAL, NEXT: REDIRECT_URL_VAL},
        expected_headers={REDIRECT_HEADER: REDIRECT_URL_VAL},
        expect_access_token=True,
    ),
    LoginLogoutTestCase(
        id="login_with_email",
        data={USERNAME_OR_EMAIL: EMAIL_VAL, PASSWORD: PASSWORD_VAL},
        expected_headers={REDIRECT_HEADER: "/"},
        expect_access_token=True,
    ),
    LoginLogoutTestCase(
        id="wrong_password",
        data={USERNAME_OR_EMAIL: USERNAME_VAL, PASSWORD: "wrong_password"},
        expected_strings=["Incorrect username or password", USERNAME_VAL],
        expected_status_code=status.HTTP_401_UNAUTHORIZED,
    ),
    LoginLogoutTestCase(
        id="non_existent_user",
        data={USERNAME_OR_EMAIL: "non_existent_user", PASSWORD: PASSWORD_VAL},
        expected_strings=["Incorrect username or password"],
        expected_status_code=status.HTTP_401_UNAUTHORIZED,
    ),
    LoginLogoutTestCase(
        id="missing_username",
        data={USERNAME_OR_EMAIL: BLANK, PASSWORD: PASSWORD_VAL},
        expected_strings=[
            "Invalid form field(s)",
            "Field must be between 3 and 100 characters long",
        ],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    LoginLogoutTestCase(
        id="missing_password",
        data={USERNAME_OR_EMAIL: USERNAME_VAL, PASSWORD: BLANK},
        expected_strings=[
            "Invalid form field(s)",
            "Field must be between 8 and 100 characters long",
        ],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
]


@pytest.mark.usefixtures("basic_user_module")
@LoginLogoutTestCase.parametrize(LOGIN_POST_TEST_CASES)
def test_login_post(test_client: TestClient, test_case: LoginLogoutTestCase):
    """Test that the login post page."""
    response = test_client.post("/login", data=test_case.data)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    for string in test_case.unexpected_strings:
        assert string not in response.text
    if test_case.expect_access_token:
        assert "access_token" in response.cookies
        assert "access_token" in response.headers.get("set-cookie", "")
    else:
        assert "access_token" not in response.cookies
        assert "access_token" not in response.headers.get("set-cookie", "")


LOGOUT_TEST_CASES = [
    LoginLogoutTestCase(
        id="logout",
        expected_strings=["Web Alchemist & Python Craftsman"],  # Redirected to home page
    ),
    LoginLogoutTestCase(
        id="logout_redirect",
        data={NEXT: "/experience"},
        expected_strings=["Professional Journey"],  # Redirected to experience page
    ),
]


# ------------------------- Logout ------------------------
@pytest.mark.usefixtures("basic_user_module")
@LoginLogoutTestCase.parametrize(LOGOUT_TEST_CASES)
def test_logout_post(test_client: TestClient, test_case: LoginLogoutTestCase):
    """Test that the logout post page."""
    # first login]
    login_data: dict[str, str] = {USERNAME_OR_EMAIL: USERNAME_VAL, PASSWORD: PASSWORD_VAL}
    response = test_client.post("/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    # Should have access token cookie from login
    assert "access_token" in response.cookies

    # Then logout
    response = test_client.post("/logout", data=test_case.data)
    assert response.status_code == test_case.expected_status_code

    # Should not have access token cookie after logout
    assert "access_token" not in response.cookies
    assert "access_token" not in response.headers.get("set-cookie", "")

    for string in test_case.expected_strings:
        assert string in response.text


# ------------------------- Register ------------------------
def test_get_register_form_no_redirect_url(test_client: TestClient):
    """Test that the register form is displayed."""
    response = test_client.get("/register")
    assert response.status_code == status.HTTP_200_OK
    assert "Register" in response.text


def test_get_register_form_with_redirect_url(test_client: TestClient):
    """Test that the register form is displayed."""
    response = test_client.get("/register", params={"next": REDIRECT_URL_VAL})
    assert response.status_code == status.HTTP_200_OK
    assert "Register" in response.text
    assert REDIRECT_URL_VAL in response.text


# ----------------------- User settings ---------------------
def test_get_user_settings_not_logged_in(test_client: TestClient):
    """Test that the user settings page is not accessible if not logged in."""
    response = test_client.get("/user-settings")
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In" in response.text
    assert "User Settings" not in response.text


def test_get_user_settings_logged_in(
    test_client: TestClient, logged_in_basic_user_module: db_models.User
):
    """Test that the user settings page is accessible if logged in."""
    user = logged_in_basic_user_module
    response = test_client.get("/user-settings")
    assert response.status_code == status.HTTP_200_OK
    assert "User Settings" in response.text
    assert user.username in response.text
    assert user.email in response.text
    assert user.full_name in response.text
