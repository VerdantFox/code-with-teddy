"""test_main: tests for the main pages."""

import re

from playwright.sync_api import Page, expect

from tests import TestCase
from tests.playwright_tests import helpers
from tests.playwright_tests.conftest import UIDetails


class BasicPageTestCase(TestCase):
    """Some basic page detail expectations."""

    endpoint: str
    title: str
    h1: str


BASIC_PAGE_TEST_CASES = [
    BasicPageTestCase(
        id="about",
        endpoint="",
        title="About",
        h1="Web Alchemist & Python Craftsman",
    ),
    BasicPageTestCase(
        id="projects",
        endpoint="/projects",
        title="Projects",
        h1="Tech Playground",
    ),
    BasicPageTestCase(
        id="experience",
        endpoint="/experience",
        title="Experience",
        h1="Professional Journey",
    ),
    BasicPageTestCase(
        id="blog",
        endpoint="/blog",
        title="Blog",
        h1="Code Chronicles",
    ),
    BasicPageTestCase(
        id="login",
        endpoint="/login",
        title="Login",
        h1="Sign In",
    ),
    BasicPageTestCase(
        id="register",
        endpoint="/register",
        title="Register",
        h1="Register",
    ),
]


@BasicPageTestCase.parametrize(BASIC_PAGE_TEST_CASES)
def test_page_essentials(
    page_session: Page, ui_details: UIDetails, test_case: BasicPageTestCase
) -> None:
    """Test some expectations about pre-determined pages."""
    page = helpers.goto(page_session, f"{ui_details.url}{test_case.endpoint}")
    full_title = f"{test_case.title} | Teddy Williams"
    expect(page).to_have_title(full_title)
    expect(page.locator("h1")).to_have_text(test_case.h1)
    helpers.assert_page_links_work(page)


def test_dark_mode(page_session: Page, ui_details: UIDetails) -> None:
    """Test the dark mode toggle."""
    page = helpers.goto(page_session, ui_details.url)
    html_locator = page.locator("html")
    body_locator = page.locator("body")
    dark_class = re.compile(r"dark")  # Need regex or match *all* classes
    dark_bg_color = "rgb(28, 25, 23)"

    # Initial state is light mode
    expect(html_locator).not_to_have_class(dark_class)
    expect(body_locator).not_to_have_css("background-color", dark_bg_color)

    # Toggle to dark mode
    page.get_by_label("Switch to dark theme").click()
    expect(html_locator).to_have_class(dark_class)
    expect(body_locator).to_have_css("background-color", dark_bg_color)

    # Dark mode should persist across pages
    page.goto(f"{ui_details.url}/experience")
    expect(html_locator).to_have_class(dark_class)
    expect(body_locator).to_have_css("background-color", dark_bg_color)

    # Toggle back to light mode
    page.get_by_label("Switch to light theme").click()
    expect(html_locator).not_to_have_class(dark_class)
    expect(body_locator).not_to_have_css("background-color", dark_bg_color)
