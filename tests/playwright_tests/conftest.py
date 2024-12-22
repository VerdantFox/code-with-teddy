"""conftest: configuration file for playwright tests."""

import os
from collections.abc import Generator
from typing import Any

import dotenv
import pytest
from playwright.sync_api import Browser, Page, expect

from app.settings import Environment
from tests.playwright_tests import ENVIRONMENT_MAP, UIDetails

IGNORED_CONSOLE_MESSAGES = {
    # Sentry error for over limit of profiling requests
    "Failed to load resource: the server responded with a status of 429 ()"
}


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
    console_msg_set = set(console_msgs) - IGNORED_CONSOLE_MESSAGES
    assert not console_msg_set


@pytest.fixture
def page(page: Page) -> Generator[Page, Any, Any]:
    """Ensure the console is empty after each test for the function-scoped page."""
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(msg.text))
    yield page
    console_msg_set = set(console_msgs) - IGNORED_CONSOLE_MESSAGES
    assert not console_msg_set


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
    console_msg_set = set(console_msgs) - IGNORED_CONSOLE_MESSAGES
    assert not console_msg_set


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
    console_msg_set = set(console_msgs) - IGNORED_CONSOLE_MESSAGES
    assert not console_msg_set


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
    console_msg_set = set(console_msgs) - IGNORED_CONSOLE_MESSAGES
    assert not console_msg_set


def login_basic(page: Page, ui_details: UIDetails) -> None:
    """Login to the UI."""
    login(
        page=page,
        base_url=ui_details.url,
        username=ui_details.basic_username,
        password=ui_details.basic_password,
    )
    expect(page.locator("div").filter(has_text="You are logged in!").nth(1)).to_be_visible()


def login_admin(page: Page, ui_details: UIDetails) -> None:
    """Login to the UI."""
    login(
        page=page,
        base_url=ui_details.url,
        username=ui_details.admin_username,
        password=ui_details.admin_password,
    )
    expect(page.locator("div").filter(has_text="You are logged in!").nth(1)).to_be_visible()


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
    all_opt = request.config.getoption("--all")
    playwright_opt = str(request.config.getoption("--playwright")).upper()
    env_opt = "local" if all_opt else playwright_opt  # pragma: no branch
    env_opt = env_opt.upper()

    try:
        environment = Environment[env_opt]
    except KeyError as e:  # pragma: no cover
        msg = (
            f"Invalid environment: {env_opt!r}. "
            f"Valid environments are: {[e.name for e in Environment]}"
        )
        raise pytest.UsageError(msg) from e

    dotenv.load_dotenv(".env.local")
    dotenv.load_dotenv(".env")
    lower_env = {k.casefold(): v for k, v in os.environ.items()}

    basic_username_key = f"{environment.casefold()}_basic_username"
    basic_password_key = f"{env_opt.casefold()}_basic_password"
    admin_username_key = f"{env_opt.casefold()}_admin_username"
    admin_password_key = f"{env_opt.casefold()}_admin_password"

    basic_username = lower_env.get(basic_username_key, "")
    basic_password = lower_env.get(basic_password_key, "")
    admin_username = lower_env.get(admin_username_key, "")
    admin_password = lower_env.get(admin_password_key, "")

    if not all(
        [basic_username, basic_password, admin_username, admin_password]
    ):  # pragma: no cover
        err_msg = (
            f"{basic_username_key}, {basic_password_key}, {admin_username_key},"
            f" and {admin_password} must be set in the environment."
        )
        raise ValueError(err_msg)

    return UIDetails(
        environment=environment,
        url=ENVIRONMENT_MAP[environment],
        basic_username=basic_username,
        basic_password=basic_password,
        admin_username=admin_username,
        admin_password=admin_password,
    )
