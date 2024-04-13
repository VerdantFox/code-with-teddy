"""conftest: configuration file for playwright tests."""

import os
from collections.abc import Generator
from typing import Any

import dotenv
import pytest
from playwright.sync_api import Browser, Page

from tests import Environment
from tests.playwright_tests import ENVIRONMENT_MAP, UIDetails


@pytest.fixture(scope="session", name="page_session_session")
def fixture_page_session_session(browser: Browser) -> Generator[Page, Any, Any]:
    """Create a session scoped page.

    This fixture is for a non-logged in session.
    """
    context = browser.new_context()
    yield context.new_page()
    context.close()


@pytest.fixture(name="page_session")
def fixture_page_session(page_session_session: Page) -> Generator[Page, Any, Any]:
    """Ensure the console is empty after each test for the session-scoped page."""
    page = page_session_session
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(msg.text))
    yield page
    assert not console_msgs


@pytest.fixture()
def page(page: Page) -> Generator[Page, Any, Any]:
    """Ensure the console is empty after each test for the function-scoped page."""
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(msg.text))
    yield page
    assert not console_msgs


@pytest.fixture(scope="session", name="login_basic_session_page_session")
def fixture_session_basic_login_session(
    ui_details: UIDetails,
    browser: Browser,
) -> Generator[Page, Any, Any]:
    """Login to the UI as a basic user once per session."""
    context = browser.new_context()
    page = context.new_page()
    login_basic(page=page, ui_details=ui_details)
    yield page
    context.close()


@pytest.fixture(name="login_basic_session_page")
def fixture_session_basic_login(
    login_basic_session_page_session: Page,
) -> Generator[Page, Any, Any]:
    """Ensure the console is empty after each test for the basic login session-scoped page."""
    page = login_basic_session_page_session
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(msg.text))
    yield page
    assert not console_msgs


@pytest.fixture(scope="session", name="login_admin_session_page_session")
def fixture_session_admin_login_session(
    ui_details: UIDetails,
    browser: Browser,
) -> Generator[Page, Any, Any]:
    """Login to the UI as an admin user once per session."""
    context = browser.new_context()
    page = context.new_page()
    login_admin(page=page, ui_details=ui_details)
    yield page
    context.close()


@pytest.fixture(name="login_admin_session_page")
def fixture_session_admin_login(
    login_admin_session_page_session: Page,
) -> Generator[Page, Any, Any]:
    """Ensure the console is empty after each test for the admin login session-scoped page."""
    page = login_admin_session_page_session
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(msg.text))
    yield page
    assert not console_msgs


@pytest.fixture(name="login_basic_once_page")
def fixture_login_basic_once(
    ui_details: UIDetails,
    page: Page,
) -> Generator[Page, Any, Any]:
    """Login to the UI as a basic user once per test."""
    login_basic(page=page, ui_details=ui_details)
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(msg.text))
    yield page
    assert not console_msgs


def login_basic(page: Page, ui_details: UIDetails) -> None:
    """Login to the UI."""
    login(
        page=page,
        base_url=ui_details.url,
        username=ui_details.basic_username,
        password=ui_details.basic_password,
    )


def login_admin(page: Page, ui_details: UIDetails) -> None:
    """Login to the UI."""
    login(
        page=page,
        base_url=ui_details.url,
        username=ui_details.admin_username,
        password=ui_details.admin_password,
    )


def login(page: Page, base_url: str, username: str, password: str) -> None:
    """Login to the UI."""
    page.goto(f"{base_url}/login")
    page.fill("#username_or_email", username)
    page.fill("#password", password)
    page.get_by_role("button", name="Log in").click()


def logout(page: Page, base_url: str) -> None:
    """Logout from the UI."""
    page.goto(f"{base_url}/logout")


@pytest.fixture(scope="session", name="ui_details")
def fixture_get_integration_environment(request: pytest.FixtureRequest) -> UIDetails:
    """Set the environment for integration tests."""
    dotenv.load_dotenv()
    basic_username = os.environ.get("BASIC_USERNAME", "")
    basic_password = os.environ.get("BASIC_PASSWORD", "")
    admin_username = os.environ.get("ADMIN_USERNAME", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not all(
        [basic_username, basic_password, admin_username, admin_password]
    ):  # pragma: no cover
        err_msg = (
            "BASIC_USERNAME, BASIC_PASSWORD, ADMIN_USERNAME, and ADMIN_PASSWORD"
            " must be set in the environment."
        )
        raise ValueError(err_msg)

    all_opt = request.config.getoption("--all")
    playwright_opt = str(request.config.getoption("--playwright")).upper()
    env_opt = "LOCAL" if all_opt else playwright_opt  # pragma: no branch

    try:
        environment = Environment[env_opt]
    except KeyError as e:  # pragma: no cover
        msg = (
            f"Invalid environment: {env_opt!r}. "
            f"Valid environments are: {[e.name for e in Environment]}"
        )
        raise pytest.UsageError(msg) from e

    return UIDetails(
        url=ENVIRONMENT_MAP[environment],
        basic_username=basic_username,
        basic_password=basic_password,
        admin_username=admin_username,
        admin_password=admin_password,
    )
