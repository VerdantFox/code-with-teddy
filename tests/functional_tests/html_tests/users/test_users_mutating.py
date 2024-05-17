"""test_users_mutating: test users mutating endpoints."""

from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.datastore import db_models
from app.services.media import media_handler
from tests import TEST_MEDIA_DATA_PATH, TestCase
from tests.data import models as test_models
from tests.functional_tests import BASE_URL


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""


# ------------------------- Register ------------------------
class RegisterTestCase(TestCase):
    """Test case for the register page."""

    data: dict[str, str] = {}  # noqa: RUF012
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012
    response_url: str = ""


# Form fields
EMAIL = "email"
USERNAME = "username"
NAME: str = "name"
PASSWORD = "password"
CONFIRM_PASSWORD = "confirm_password"
REDIRECT_URL = "redirect_url"
NEXT = "next"

# Form field values
EMAIL_VAL: str = "new@email.com"
USERNAME_VAL: str = "new_user"
NAME_VAL: str = "New User"
PASSWORD_VAL: str = "password1"
CONFIRM_PASSWORD_VAL: str = "password1"
REDIRECT_URL_VAL: str = "/experience"
BLANK = ""

# Others
LOGIN_PAGE = "Don't have an account?"
REGISTER_PAGE = "Already have an account?"
ENCODED_EMAIL_VAL = quote(EMAIL_VAL)
ENCODED_REDIRECT_URL_VAL = quote(REDIRECT_URL_VAL, safe="")
INVALID_FORM_FIELDS = "Invalid form field(s)."

REGISTER_TEST_CASES = [
    RegisterTestCase(
        id="happy_path_no_redirect",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: CONFIRM_PASSWORD_VAL,
            REDIRECT_URL: BLANK,
        },
        expected_strings=[LOGIN_PAGE, EMAIL_VAL],
        response_url=f"{BASE_URL}/login?username_or_email={ENCODED_EMAIL_VAL}&next=",
    ),
    RegisterTestCase(
        id="happy_path_with_redirect",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: CONFIRM_PASSWORD_VAL,
            REDIRECT_URL: REDIRECT_URL_VAL,
        },
        expected_strings=[LOGIN_PAGE, EMAIL_VAL],
        response_url=f"{BASE_URL}/login?username_or_email={ENCODED_EMAIL_VAL}&next={ENCODED_REDIRECT_URL_VAL}",
    ),
    RegisterTestCase(
        id="blank_fields",
        data={
            EMAIL: BLANK,
            USERNAME: BLANK,
            NAME: BLANK,
            PASSWORD: BLANK,
            CONFIRM_PASSWORD: BLANK,
            REDIRECT_URL: BLANK,
        },
        expected_strings=[
            REGISTER_PAGE,
            INVALID_FORM_FIELDS,
            "Field must be between 1 and 100 characters long.",
            "Field must be between 3 and 100 characters long.",
            "Field must be between 8 and 100 characters long.",
        ],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    RegisterTestCase(
        id="invalid_email",
        data={
            EMAIL: "invalid_email",
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: CONFIRM_PASSWORD_VAL,
            REDIRECT_URL: REDIRECT_URL_VAL,
        },
        expected_strings=[REGISTER_PAGE, INVALID_FORM_FIELDS, "Invalid email address."],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    RegisterTestCase(
        id="password_mismatch",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: "password2",
            REDIRECT_URL: REDIRECT_URL_VAL,
        },
        expected_strings=[REGISTER_PAGE, INVALID_FORM_FIELDS, "Passwords must match"],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    RegisterTestCase(
        id="repeat_username",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: test_models.ADMIN_USER[test_models.UserModelKeys.USERNAME],
            NAME: NAME_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: CONFIRM_PASSWORD_VAL,
            REDIRECT_URL: REDIRECT_URL_VAL,
        },
        expected_strings=[REGISTER_PAGE, "Username taken."],
        expected_status_code=status.HTTP_400_BAD_REQUEST,
    ),
    RegisterTestCase(
        id="repeat_email",
        data={
            EMAIL: test_models.ADMIN_USER[test_models.UserModelKeys.EMAIL],
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: CONFIRM_PASSWORD_VAL,
            REDIRECT_URL: REDIRECT_URL_VAL,
        },
        expected_strings=[REGISTER_PAGE, "Email already exists for another account."],
        expected_status_code=status.HTTP_400_BAD_REQUEST,
    ),
]


@pytest.mark.usefixtures("admin_user")
@RegisterTestCase.parametrize(REGISTER_TEST_CASES)
def test_register_user_post(test_client: TestClient, test_case: RegisterTestCase) -> None:
    """Test the register page."""
    response = test_client.post("/register", data=test_case.data)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    if test_case.response_url:
        assert test_case.response_url == response.url


# ---------------------- User settings ---------------------
def test_user_settings_post_as_guest(test_client: TestClient) -> None:
    """Test the user settings page as a guest."""
    response = test_client.post("/user-settings")
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In</h1>" in response.text


class UserSettingsTestCase(TestCase):
    """Test case for the user settings page."""

    data: dict[str, str] = {}  # noqa: RUF012
    files: Any = None
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012


# Form fields
TIMEZONE = "timezone"
AVATAR_URL = "avatar_url"
AVATAR_UPLOAD = "avatar_upload"

# Form field values
TIMEZONE_VAL: str = "US/Pacific"
DEFAULT_TZ = "UTC"
AVATAR_URL_VAL: str = "https://example.com/avatar.png"
INVALID_FILE_EXT = "Invalid file extension. Allowed: jpg, jpeg, png, svg, webp."

# Good images
PNG_FILE = TEST_MEDIA_DATA_PATH / "test.png"
JPG_FILE = TEST_MEDIA_DATA_PATH / "test.jpg"
SVG_FILE = TEST_MEDIA_DATA_PATH / "test.svg"
WEBP_FILE = TEST_MEDIA_DATA_PATH / "test.webp"

# Bad image
GIF_FILE = TEST_MEDIA_DATA_PATH / "test.gif"
MP4_FILE = TEST_MEDIA_DATA_PATH / "test.mp4"


USER_SETTINGS_TEST_CASES = [
    UserSettingsTestCase(
        id="success_basic",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: PASSWORD_VAL,
        },
        expected_strings=[USERNAME_VAL, NAME_VAL, TIMEZONE_VAL],
    ),
    UserSettingsTestCase(
        id="success_with_avatar_url",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
            AVATAR_URL: AVATAR_URL_VAL,
        },
        expected_strings=[AVATAR_URL_VAL, USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="success_with_avatar_upload_png",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        files={AVATAR_UPLOAD: (PNG_FILE.name, PNG_FILE.read_bytes())},
        expected_strings=[".png", USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="success_with_avatar_upload_jpg_and_url",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
            AVATAR_URL: AVATAR_URL_VAL,  # File upload wins
        },
        files={AVATAR_UPLOAD: (JPG_FILE.name, JPG_FILE.read_bytes())},
        expected_strings=[".jpg", USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="success_with_avatar_upload_svg",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        files={AVATAR_UPLOAD: (SVG_FILE.name, SVG_FILE.read_bytes())},
        expected_strings=[".svg", USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="success_with_avatar_upload_webp",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        files={AVATAR_UPLOAD: (WEBP_FILE.name, WEBP_FILE.read_bytes())},
        expected_strings=[".webp", USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="fail_with_avatar_upload_gif",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        files={AVATAR_UPLOAD: (GIF_FILE.name, GIF_FILE.read_bytes())},
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=[INVALID_FILE_EXT, USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="fail_with_avatar_upload_mp4",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        files={AVATAR_UPLOAD: (MP4_FILE.name, MP4_FILE.read_bytes())},
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=[INVALID_FILE_EXT, USERNAME_VAL],
    ),
    UserSettingsTestCase(
        id="blank_fields",
        data={
            EMAIL: BLANK,
            USERNAME: BLANK,
            NAME: BLANK,
            TIMEZONE: BLANK,
        },
        expected_strings=[
            INVALID_FORM_FIELDS,
            "Field must be between 1 and 100 characters long.",
            "Field must be between 3 and 100 characters long.",
        ],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    UserSettingsTestCase(
        id="invalid_email",
        data={
            EMAIL: "invalid_email",
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        expected_strings=["Invalid email address."],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    UserSettingsTestCase(
        id="passwords_mismatch",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
            PASSWORD: PASSWORD_VAL,
            CONFIRM_PASSWORD: "password2",
        },
        expected_strings=["Passwords must match"],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    UserSettingsTestCase(
        id="repeat_username",
        data={
            EMAIL: EMAIL_VAL,
            USERNAME: test_models.ADMIN_USER[test_models.UserModelKeys.USERNAME],
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        expected_strings=["Username taken."],
        expected_status_code=status.HTTP_400_BAD_REQUEST,
    ),
    UserSettingsTestCase(
        id="repeat_email",
        data={
            EMAIL: test_models.ADMIN_USER[test_models.UserModelKeys.EMAIL],
            USERNAME: USERNAME_VAL,
            NAME: NAME_VAL,
            TIMEZONE: TIMEZONE_VAL,
        },
        expected_strings=["Email already exists for another account."],
        expected_status_code=status.HTTP_400_BAD_REQUEST,
    ),
]


@pytest.mark.usefixtures("logged_in_basic_user", "admin_user")
@UserSettingsTestCase.parametrize(USER_SETTINGS_TEST_CASES)
def test_user_settings_post_as_user(
    test_client: TestClient,
    test_case: UserSettingsTestCase,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test the user settings page."""
    _mock_avatar_upload_folder(tmp_path, mocker)
    response = test_client.post("/user-settings", data=test_case.data, files=test_case.files)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text

    if response.status_code == status.HTTP_200_OK:
        assert INVALID_FORM_FIELDS not in response.text
    else:
        assert INVALID_FORM_FIELDS in response.text


def test_repeat_avatar_image_is_deleted(
    test_client: TestClient,
    logged_in_basic_user: db_models.User,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test that the repeat avatar image is deleted."""
    _mock_avatar_upload_folder(tmp_path, mocker)

    response = test_client.post(
        "/user-settings",
        data={
            EMAIL: logged_in_basic_user.email,
            USERNAME: logged_in_basic_user.username,
            NAME: logged_in_basic_user.full_name,
            TIMEZONE: logged_in_basic_user.timezone,
        },
        files={AVATAR_UPLOAD: ("avatar.png", PNG_FILE.read_bytes())},
    )
    assert response.status_code == status.HTTP_200_OK
    assert INVALID_FORM_FIELDS not in response.text

    response = test_client.post(
        "/user-settings",
        data={
            EMAIL: logged_in_basic_user.email,
            USERNAME: logged_in_basic_user.username,
            NAME: logged_in_basic_user.full_name,
            TIMEZONE: logged_in_basic_user.timezone,
            AVATAR_URL: AVATAR_URL_VAL,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert INVALID_FORM_FIELDS not in response.text


def _mock_avatar_upload_folder(tmp_path: Path, mocker: MockerFixture) -> Path:
    """Mock the avatar upload folder."""
    tmp_avatar_upload_folder_path = tmp_path / "static" / "media" / "avatars"
    tmp_avatar_upload_folder_path.mkdir(parents=True, exist_ok=True)
    mocker.patch.object(media_handler, "AVATAR_UPLOAD_FOLDER", tmp_avatar_upload_folder_path)
    return tmp_avatar_upload_folder_path
