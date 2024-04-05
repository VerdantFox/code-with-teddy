"""test_blog_list: test the blog list page."""

import re

from playwright.sync_api import Page, expect

from tests.playwright_tests import helpers
from tests.playwright_tests.conftest import UIDetails


def test_blog_list_compact_view_and_advanced_search_on_off(
    page: Page, ui_details: UIDetails
) -> None:
    """Test the blog list page functionality."""
    url = f"{ui_details.url}/blog"
    page.goto(url)

    # Assert the blog list is in compact view by default
    expect(page.get_by_label("Compact view")).to_be_checked()
    expect(page.get_by_text("Last Updated:").first).not_to_be_visible()

    # Switch to detailed view
    page.get_by_label("Compact view").click()
    expect(page.get_by_label("Compact view")).not_to_be_checked()
    expect(page.get_by_text("Last Updated:").first).to_be_visible()

    # Advanced search not visible
    expect(page.get_by_label("tags")).not_to_be_visible()

    # Open advanced search and it should become visible
    page.get_by_role("button", name="Advanced").click()
    expect(page.get_by_label("tags")).to_be_visible()

    # Switch the alternate page and back
    page.get_by_label("Main Navigation", exact=True).get_by_role("link", name="Experience").click()
    expect(page.get_by_role("heading", name="Professional Journey")).to_be_visible()
    page.get_by_label("Main Navigation", exact=True).get_by_role("link", name="blog").click()

    # Compact view state should be preserved
    expect(page.get_by_label("Compact view")).not_to_be_checked()
    expect(page.get_by_text("Last Updated:").first).to_be_visible()

    # Switch back to not compact view
    page.get_by_label("Compact view").click()
    expect(page.get_by_label("Compact view")).to_be_checked()
    expect(page.get_by_text("Last Updated:").first).not_to_be_visible()

    # Advanced search state should be preserved
    expect(page.get_by_label("tags")).to_be_visible()

    # Switch back to advanced search closed
    page.get_by_role("button", name="Advanced").click()
    expect(page.get_by_label("tags")).not_to_be_visible()


def test_blog_list_search(page: Page, ui_details: UIDetails) -> None:
    # sourcery skip: extract-duplicate-method
    """Test the blog list search functionality."""
    url = f"{ui_details.url}/blog"
    page.goto(url)
    bp_title_locator = page.locator(".bp-title")

    count_before = bp_title_locator.count()
    assert count_before > 1
    first_article_text = bp_title_locator.first.inner_text()

    # Search for the first article
    page.get_by_placeholder("Search blog posts").fill(first_article_text)
    page.get_by_placeholder("Search blog posts").press("Enter")

    # Check that the first article is the only one visible
    expect(bp_title_locator).to_have_count(1)
    assert bp_title_locator.first.inner_text() == first_article_text

    # Clear the search
    page.get_by_placeholder("Search blog posts").fill("")
    page.get_by_placeholder("Search blog posts").press("Enter")

    # Check that all articles are visible
    expect(bp_title_locator).to_have_count(count_before)


def test_go_to_article(page_session: Page, ui_details: UIDetails) -> None:
    """Test the blog list page functionality."""
    url = f"{ui_details.url}/blog"
    page = helpers.goto(page_session, url)

    # Get the first article title
    first_article_title = page.locator(".bp-title").first.inner_text()
    first_article_heading_locator = page.locator("h1", has_text=re.compile(first_article_title))

    # Assert not on the article page
    expect(first_article_heading_locator).not_to_be_visible()

    # Click on the first article
    page.locator("a").filter(has_text=re.compile(first_article_title)).first.click()

    # Check that the article page is visible
    expect(first_article_heading_locator).to_be_visible()
