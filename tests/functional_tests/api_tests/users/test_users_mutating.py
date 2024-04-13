"""test_users_mutating: mutating tests for the users API routes."""

from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.datastore import db_models
from tests import PYDANTIC_VERSION, TestCase
from tests.data import models as test_models
from tests.functional_tests.api_tests.conftest import post_for_token

USERS_ENDPOINT = "/api/v1/users"

PERMISSIONS_ERROR = {"detail": "You do not have permission to perform this action"}
UNAUTHENTICATED_ERROR = {"detail": "Not authenticated"}

# fields
ID = test_models.UserModelKeys.ID
USERNAME = test_models.UserModelKeys.USERNAME
EMAIL = test_models.UserModelKeys.EMAIL
FULL_NAME = test_models.UserModelKeys.FULL_NAME
PASSWORD = test_models.UserModelKeys.PASSWORD
AVATAR_LOCATION = test_models.UserModelKeys.AVATAR_LOCATION
TIMEZONE = test_models.UserModelKeys.TIMEZONE
ROLE = test_models.UserModelKeys.ROLE
IS_ACTIVE = test_models.UserModelKeys.IS_ACTIVE


@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module."""


@pytest.fixture(name="clean_db_users")
async def _clean_db_users_fixture_function(anyio_backend: str, db_session: AsyncSession) -> None:  # noqa: ARG001 (unused-arg)
    # sourcery skip: merge-comparisons
    """Clean users from the db except the basic and admin user."""
    await db_session.execute(
        delete(db_models.User).where(
            ~db_models.User.username.in_(
                [test_models.BASIC_USER[USERNAME], test_models.ADMIN_USER[USERNAME]]
            )
        )
    )
    await db_session.commit()


@pytest.fixture(name="reset_basic_user")
async def _reset_basic_user_fixture_function(
    anyio_backend: str,  # noqa: ARG001 (unused-arg)
    db_session: AsyncSession,
    basic_user_module: db_models.User,
) -> AsyncGenerator[None, None]:
    """Reset the basic user."""
    user_before = _get_user_before(basic_user_module)
    yield
    await _reset_user(db_session=db_session, user_before=user_before)


def _get_user_before(user: db_models.User) -> dict[str, Any]:
    """Return the user before changes."""
    return {
        ID: user.id,
        USERNAME: user.username,
        EMAIL: user.email,
        FULL_NAME: user.full_name,
        IS_ACTIVE: user.is_active,
        ROLE: user.role,
        PASSWORD: user.password_hash,
        AVATAR_LOCATION: user.avatar_location,
        TIMEZONE: user.timezone,
    }


async def _reset_user(db_session: AsyncSession, user_before: dict[str, Any]) -> db_models.User:
    """Reset a user."""
    results = await db_session.execute(
        select(db_models.User).filter(db_models.User.id == user_before[ID])
    )
    user: db_models.User = results.scalars().one()
    user.username = user_before[USERNAME]
    user.email = user_before[EMAIL]
    user.full_name = user_before[FULL_NAME]
    user.is_active = user_before[IS_ACTIVE]
    user.role = user_before[ROLE]
    user.password_hash = user_before[PASSWORD]
    user.avatar_location = user_before[AVATAR_LOCATION]
    user.timezone = user_before[TIMEZONE]
    await db_session.commit()
    await db_session.refresh(user)
    return user


USER_IN_BASE = {
    USERNAME: "simple_user",
    EMAIL: "simple@email.com",
    FULL_NAME: "Simple User",
}
USER_IN_CREATE_BASIC = {
    **USER_IN_BASE,
    PASSWORD: "password",
}
USER_IN_CREATE_FULL = {
    **USER_IN_CREATE_BASIC,
    AVATAR_LOCATION: "avatar",
    TIMEZONE: "PST",
}


def test_create_user_as_guest_fails(test_client: TestClient) -> None:
    """Should return an unauthorized error as a guest."""
    response = test_client.post(USERS_ENDPOINT)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == UNAUTHENTICATED_ERROR


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_create_user_as_basic_user_fails(test_client: TestClient) -> None:
    """Should return an unauthorized error as a user."""
    response = test_client.post(USERS_ENDPOINT, json=USER_IN_CREATE_BASIC)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == PERMISSIONS_ERROR


class CreateUpdateUserTestCase(TestCase):
    """Test case for creating or updating a user."""

    body: dict[str, Any]
    expected_status_code: int
    expected_response_body: dict[str, Any]


CREATE_USER_TEST_CASES = [
    CreateUpdateUserTestCase(
        id="basic_user",
        body=USER_IN_CREATE_BASIC,
        expected_status_code=status.HTTP_201_CREATED,
        expected_response_body={
            **USER_IN_BASE,
            ID: -1,
            TIMEZONE: "UTC",
            AVATAR_LOCATION: None,
            ROLE: "user",
            IS_ACTIVE: True,
        },
    ),
    CreateUpdateUserTestCase(
        id="full_user",
        body=USER_IN_CREATE_FULL,
        expected_status_code=status.HTTP_201_CREATED,
        expected_response_body={
            **USER_IN_CREATE_FULL,
            ID: -1,
            ROLE: "user",
            IS_ACTIVE: True,
        },
    ),
    CreateUpdateUserTestCase(
        id="username_exists",
        body={**USER_IN_CREATE_BASIC, USERNAME: test_models.ADMIN_USER[USERNAME]},
        expected_status_code=status.HTTP_409_CONFLICT,
        expected_response_body={"detail": "User with username 'admin_user' already exists."},
    ),
    CreateUpdateUserTestCase(
        id="email_exists",
        body={**USER_IN_CREATE_BASIC, EMAIL: test_models.ADMIN_USER[EMAIL]},
        expected_status_code=status.HTTP_409_CONFLICT,
        expected_response_body={"detail": "User with email 'admin@email.com' already exists."},
    ),
    CreateUpdateUserTestCase(
        id="missing_fields",
        body={},
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_response_body={
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "username"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/missing",
                },
                {
                    "type": "missing",
                    "loc": ["body", "email"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/missing",
                },
                {
                    "type": "missing",
                    "loc": ["body", "full_name"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/missing",
                },
                {
                    "type": "missing",
                    "loc": ["body", "password"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/missing",
                },
            ]
        },
    ),
    CreateUpdateUserTestCase(
        id="invalid_fields",
        body={USERNAME: "a", EMAIL: "a", FULL_NAME: "a", PASSWORD: "a"},
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_response_body={
            "detail": [
                {
                    "type": "string_too_short",
                    "loc": ["body", "username"],
                    "msg": "String should have at least 3 characters",
                    "input": "a",
                    "ctx": {"min_length": 3},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/string_too_short",
                },
                {
                    "type": "value_error",
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address: The email address is not valid. It must have exactly one @-sign.",
                    "input": "a",
                    "ctx": {
                        "reason": "The email address is not valid. It must have exactly one @-sign."
                    },
                },
                {
                    "type": "string_too_short",
                    "loc": ["body", "full_name"],
                    "msg": "String should have at least 3 characters",
                    "input": "a",
                    "ctx": {"min_length": 3},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/string_too_short",
                },
                {
                    "type": "string_too_short",
                    "loc": ["body", "password"],
                    "msg": "String should have at least 8 characters",
                    "input": "a",
                    "ctx": {"min_length": 8},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/string_too_short",
                },
            ]
        },
    ),
]


@CreateUpdateUserTestCase.parametrize(CREATE_USER_TEST_CASES)
@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_users")
def test_create_user_as_admin_user(
    test_client: TestClient, test_case: CreateUpdateUserTestCase
) -> None:
    """Should create a user as an admin."""
    response = test_client.post(USERS_ENDPOINT, json=test_case.body)
    assert response.status_code == test_case.expected_status_code
    body = response.json()
    if test_case.expected_response_body.get(ID) == -1:
        test_case.expected_response_body.pop(ID)
        assert body.pop(ID)
    if PASSWORD in test_case.expected_response_body:
        test_case.expected_response_body.pop(PASSWORD)
    assert body == test_case.expected_response_body


def test_update_current_user_as_guest_fails(test_client: TestClient) -> None:
    """Should return an unauthorized error as a guest."""
    response = test_client.patch(f"{USERS_ENDPOINT}/current-user")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == UNAUTHENTICATED_ERROR


def test_update_user_as_guest_fails(test_client: TestClient) -> None:
    """Should return an unauthorized error as a guest."""
    response = test_client.patch(f"{USERS_ENDPOINT}/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == UNAUTHENTICATED_ERROR


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_update_other_user_as_basic_user_returns_not_found(
    test_client: TestClient, admin_user_module: db_models.User
) -> None:
    """Should return a not found error as a user."""
    response = test_client.patch(f"{USERS_ENDPOINT}/{admin_user_module.id}", json={})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}


UPDATES_BASE = {
    USERNAME: "new_username",
    EMAIL: "new_email@email.com",
    FULL_NAME: "New Name",
    AVATAR_LOCATION: "new_avatar",
    TIMEZONE: "PST",
    IS_ACTIVE: False,
}
PATCH_USER_TEST_CASES = [
    CreateUpdateUserTestCase(
        id="basic_user_updates",
        body=UPDATES_BASE,
        expected_status_code=status.HTTP_200_OK,
        expected_response_body=UPDATES_BASE,
    ),
    CreateUpdateUserTestCase(
        id="basic_user_updates_partial",
        body={USERNAME: "new_username"},
        expected_status_code=status.HTTP_200_OK,
        expected_response_body={USERNAME: "new_username"},
    ),
    CreateUpdateUserTestCase(
        id="update_password",  # not going to bother verifying
        body={PASSWORD: "new_password"},
        expected_status_code=status.HTTP_200_OK,
        expected_response_body={},
    ),
    CreateUpdateUserTestCase(
        id="update_role",
        body={ROLE: "admin"},
        expected_status_code=status.HTTP_403_FORBIDDEN,
        expected_response_body={"detail": "Cannot update role field"},
    ),
    CreateUpdateUserTestCase(
        id="update_username_exists",
        body={USERNAME: test_models.ADMIN_USER[USERNAME]},
        expected_status_code=status.HTTP_409_CONFLICT,
        expected_response_body={"detail": "User with username 'admin_user' already exists."},
    ),
    CreateUpdateUserTestCase(
        id="update_email_exists",
        body={EMAIL: test_models.ADMIN_USER[EMAIL]},
        expected_status_code=status.HTTP_409_CONFLICT,
        expected_response_body={"detail": "User with email 'admin@email.com' already exists."},
    ),
    CreateUpdateUserTestCase(
        id="update_invalid_fields",
        body={USERNAME: "a", EMAIL: "a", FULL_NAME: "a", PASSWORD: "a"},
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_response_body={
            "detail": [
                {
                    "type": "string_too_short",
                    "loc": ["body", "username"],
                    "msg": "String should have at least 3 characters",
                    "input": "a",
                    "ctx": {"min_length": 3},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/string_too_short",
                },
                {
                    "type": "value_error",
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address: The email address is not valid. It must have exactly one @-sign.",
                    "input": "a",
                    "ctx": {
                        "reason": "The email address is not valid. It must have exactly one @-sign."
                    },
                },
                {
                    "type": "string_too_short",
                    "loc": ["body", "full_name"],
                    "msg": "String should have at least 3 characters",
                    "input": "a",
                    "ctx": {"min_length": 3},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/string_too_short",
                },
                {
                    "type": "string_too_short",
                    "loc": ["body", "password"],
                    "msg": "String should have at least 8 characters",
                    "input": "a",
                    "ctx": {"min_length": 8},
                    "url": f"https://errors.pydantic.dev/{PYDANTIC_VERSION}/v/string_too_short",
                },
            ]
        },
    ),
]


@CreateUpdateUserTestCase.parametrize(PATCH_USER_TEST_CASES)
@pytest.mark.usefixtures("reset_basic_user", "admin_user_module")
def test_update_self_as_basic_current_user(
    test_client: TestClient,
    logged_in_basic_user_module: db_models.User,
    test_case: CreateUpdateUserTestCase,
) -> None:
    """Test updating self in PATCH /users/current-user."""
    user = logged_in_basic_user_module
    response = test_client.patch(f"{USERS_ENDPOINT}/current-user", json=test_case.body)
    _assert_on_user_changes(test_case=test_case, response=response, user=user)


@CreateUpdateUserTestCase.parametrize(PATCH_USER_TEST_CASES)
@pytest.mark.usefixtures("reset_basic_user", "admin_user_module")
def test_update_self_as_basic_user(
    test_client: TestClient,
    logged_in_basic_user_module: db_models.User,
    test_case: CreateUpdateUserTestCase,
) -> None:
    """Test updating self in PATCH /users/{id}."""
    user = logged_in_basic_user_module
    response = test_client.patch(f"{USERS_ENDPOINT}/{user.id}", json=test_case.body)
    _assert_on_user_changes(test_case=test_case, response=response, user=user)


def _assert_on_user_changes(
    test_case: CreateUpdateUserTestCase, response: httpx.Response, user: db_models.User
) -> None:
    """Assert on the user changes."""
    assert response.status_code == test_case.expected_status_code
    body = response.json()

    if response.status_code != status.HTTP_200_OK:
        assert body == test_case.expected_response_body
        return

    for key, value in test_case.expected_response_body.items():
        assert body[key] == value

    remainders = {
        key: value
        for key, value in user.to_dict().items()
        if key not in test_case.expected_response_body
    }
    pops = ("password_hash", "github_oauth_id", "google_oauth_id")
    for pop in pops:
        remainders.pop(pop, None)
    for key, value in remainders.items():
        assert body[key] == value


@pytest.mark.usefixtures("reset_basic_user", "logged_in_admin_user_module")
def test_admin_can_update_users_role(
    test_client: TestClient, basic_user_module: db_models.User
) -> None:
    """Should update a user's role as an admin."""
    response = test_client.patch(f"{USERS_ENDPOINT}/{basic_user_module.id}", json={ROLE: "admin"})
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body[ROLE] == "admin"


def test_delete_current_user_as_guest_fails(test_client: TestClient) -> None:
    """Should return an unauthorized error as a guest."""
    response = test_client.delete(f"{USERS_ENDPOINT}/current-user")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == UNAUTHENTICATED_ERROR


def test_delete_user_as_guest_fails(test_client: TestClient) -> None:
    """Should return an unauthorized error as a guest."""
    response = test_client.delete(f"{USERS_ENDPOINT}/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == UNAUTHENTICATED_ERROR


def test_delete_current_user_as_basic_user_succeeds(
    test_client: TestClient, basic_user_2: db_models.User
) -> None:
    """Current user should be able to delete themselves."""
    # log in as basic user
    login_headers = post_for_token(test_client, basic_user_2)
    response = test_client.delete(f"{USERS_ENDPOINT}/current-user", headers=login_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_self_user_as_basic_user_succeeds(
    test_client: TestClient, basic_user_2: db_models.User
) -> None:
    """Current user should be able to delete themselves from DELETE /users/{id}."""
    # log in as basic user
    login_headers = post_for_token(test_client, basic_user_2)
    response = test_client.delete(f"{USERS_ENDPOINT}/{basic_user_2.id}", headers=login_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.usefixtures("clean_db_users", "logged_in_basic_user_module")
def test_delete_user_as_basic_user_fails(
    test_client: TestClient, basic_user_2: db_models.User
) -> None:
    """Should fail to find delete user as basic user if not self."""
    response = test_client.delete(f"{USERS_ENDPOINT}/{basic_user_2.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}


@pytest.mark.usefixtures("clean_db_users", "logged_in_admin_user_module")
def test_delete_user_as_admin_user_succeeds(
    test_client: TestClient, basic_user_2: db_models.User
) -> None:
    """Should delete a user as an admin."""
    response = test_client.delete(f"{USERS_ENDPOINT}/{basic_user_2.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
