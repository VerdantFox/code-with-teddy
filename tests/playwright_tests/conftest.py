"""conftest: configuration file for playwright tests."""

import os
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import dotenv
import pytest
from playwright.sync_api import Browser, Page

from tests import Environment

ENVIRONMENT_MAP = {
    Environment.LOCAL: "http://localhost:8000",
    Environment.PROD: "https://not-yet-determined.com",
}


@dataclass
class UIDetails:
    """Class to hold authentication details."""

    url: str
    basic_username: str
    basic_password: str
    admin_username: str
    admin_password: str


@pytest.fixture(scope="session", name="browser")
def fixture_browser(browser: Browser) -> Browser:
    """Create a browser context for the session."""
    return browser


@pytest.fixture(scope="session", name="page_session")
def fixture_page_session(browser: Browser) -> Generator[Page, Any, Any]:
    """Create a browser context for the session."""
    context = browser.new_context()
    yield context.new_page()
    context.close()


@pytest.fixture(scope="session", name="login_basic_session")
def fixture_session_basic_login(
    ui_details: UIDetails,
    browser: Browser,
) -> Generator[tuple[Page, str], Any, Any]:
    """Login to the UI as a basic user once per session."""
    context = browser.new_context()
    page = context.new_page()
    login_basic(page=page, ui_details=ui_details)
    yield page, ui_details.url
    context.close()


@pytest.fixture(scope="session", name="login_admin_session")
def fixture_session_admin_login(
    ui_details: UIDetails,
    browser: Browser,
) -> Generator[tuple[Page, str], Any, Any]:
    """Login to the UI as an admin user once per session."""
    context = browser.new_context()
    page = context.new_page()
    login_admin(page=page, ui_details=ui_details)
    yield page, ui_details.url
    context.close()


@pytest.fixture(name="login_basic_once")
def fixture_login_basic_once(
    ui_details: UIDetails,
    page: Page,
) -> tuple[Page, str]:
    """Login to the UI as a basic user once per test."""
    login_basic(page=page, ui_details=ui_details)
    return page, ui_details.url


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
    if not all([basic_username, basic_password, admin_username, admin_password]):
        err_msg = (
            "BASIC_USERNAME, BASIC_PASSWORD, ADMIN_USERNAME, and ADMIN_PASSWORD"
            " must be set in the environment."
        )
        raise ValueError(err_msg)

    integration_env_opt = str(request.config.getoption("--playwright")).upper()
    try:
        environment = Environment[integration_env_opt]
    except KeyError as e:
        msg = (
            f"Invalid environment: {integration_env_opt!r}. "
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
