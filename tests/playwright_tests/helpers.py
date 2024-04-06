"""helpers: Helper functions for playwright tests."""

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

import requests
import tenacity
from playwright.sync_api import Page


@tenacity.retry(wait=tenacity.wait_fixed(0.1), stop=tenacity.stop_after_attempt(10))
def goto(page: Page, url: str) -> Page:
    """Go to a page iff not already on that page.

    Retry logic because get a playwright connection error sometimes,
    especially right after a login; reason unknown.
    """
    if page.url == url:
        return page

    page.goto(url)
    return page


def assert_page_links_work(page: Page) -> None:
    """Assert that all links on a page are working."""
    links = _get_page_links(page)
    _assert_links_work(links)


def _get_page_links(page: Page) -> set[str]:
    """Get all links on a page."""
    links = page.query_selector_all("a")
    hrefs = {href for link in links if (href := link.get_attribute("href"))}
    return {href for href in hrefs if not href.startswith(("#", "mailto:"))}


def _assert_links_work(links: Iterable[str]) -> None:
    """Assert that all links are working.

    Pytest-playwright breaks async tests so have to do this with threads
    instead of async/await.
    """
    with ThreadPoolExecutor() as executor:
        [executor.submit(_assert_link_works, link) for link in links]


def _assert_link_works(link: str) -> None:
    """Assert that a link is working."""
    response = requests.get(link, timeout=10)
    assert response.ok
