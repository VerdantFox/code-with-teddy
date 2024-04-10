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


def test_write_edit_delete_comment_as_guest(page_session: Page, blog_post_url: str) -> None:
    """Test writing, editing, and deleting a comment as a guest."""
    page = helpers.goto(page=page_session, url=blog_post_url)

    # Submit a new comment
    page.locator("#name").fill("test comment")
    page.locator("#email").fill("test@email.com")
    page.get_by_label("I am not a robot").click()
    page.locator("#content").fill("temporary test comment...")
    page.locator("#content").first.press("Delete")
    comment_content_preview_locator = page.locator("#comment-content-base").locator("p").first
    expected = re.compile(r"temporary test comment")
    expect(comment_content_preview_locator).to_have_text(expected)
    page.get_by_role("button", name="Submit").click()
    # Comment created in toast notification is visible
    expect(page.locator("div").filter(has_text="Comment saved!").nth(1)).to_be_visible()

    # Open the comment edit
    page.wait_for_timeout(500)
    comment_locator = page.locator("article.comment").last
    edit_comment_locator = comment_locator.locator("button.edit-comment-btn")
    edit_comment_locator.click()

    # Cancel the comment
    cancel_comment_locator = page.locator("button.cancel-comment-btn").first
    expect(cancel_comment_locator).to_be_visible()
    cancel_comment_locator.click()
    expect(cancel_comment_locator).not_to_be_visible()

    # Open the comment edit again
    page.wait_for_timeout(500)
    comment_locator = page.locator("article.comment").last
    edit_comment_locator = comment_locator.locator("button.edit-comment-btn")
    edit_comment_locator.click()

    # Edit the comment
    edit_comment_h3_locator = page.locator("h3", has_text="Editing comment").first
    edit_comment_div_locator = page.locator("div.not-prose").filter(has=edit_comment_h3_locator)
    edit_textarea_locator = edit_comment_div_locator.locator("textarea").first
    edit_textarea_locator.fill("temporary test comment... updated...")
    submit_btn_locator = edit_comment_div_locator.locator("button.submit-btn").first
    page.wait_for_timeout(500)
    submit_btn_locator.click()
    # Comment updated in toast notification is visible
    expect(page.locator("div").filter(has_text="Comment updated!").nth(1)).to_be_visible()

    # Delete the comment
    page.get_by_role("button", name="Delete comment").click()
    page.get_by_role("button", name="Delete").click()
    expect(page.get_by_text("Comment deleted!")).to_be_visible()
    # Comment updated in toast notification is visible
    expect(page.locator("div").filter(has_text="Comment deleted").nth(1)).to_be_visible()
