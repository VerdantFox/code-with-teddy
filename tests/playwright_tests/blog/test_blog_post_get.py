"""test_blog_post_get: test getting an individual blog post."""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.playwright_tests import UIDetails, helpers
from tests.playwright_tests.blog import cache_blog_articles, get_article_from_cache


@pytest.fixture(name="blog_post_url")
def fixture_get_blog_post_url(page_session: Page, ui_details: UIDetails) -> str:
    """Return the URL for a blog post."""
    if cached_bp := get_article_from_cache():
        return cached_bp
    helpers.goto(page=page_session, url=f"{ui_details.url}/blog")
    cache_blog_articles(page=page_session)
    return get_article_from_cache()


def test_blog_post_toc_behavior(page_session: Page, blog_post_url: str) -> None:
    """Test getting a blog post's table of contents."""
    page = page_session
    page.goto(blog_post_url)

    # At top of page title is visible and "Title" nav link is highlighted
    expect(page.locator("h1")).to_be_in_viewport()
    highlighted = re.compile(r"blog-nav-highlight")
    expect(page.get_by_role("link", name="Title")).to_have_class(highlighted)

    # Clicking on "Comments" link scrolls to comments section and highlights "Comments" nav link
    page.get_by_role("link", name="Comments").click()
    expect(page.get_by_role("link", name="Comments")).to_have_class(highlighted)
