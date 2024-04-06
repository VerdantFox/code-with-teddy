"""__init__: blog tests package."""

from playwright.sync_api import Page

BLOG_ARTICLES: set[str] = set()


def cache_blog_articles(page: Page) -> None:
    """Cache the blog articles from the page."""
    links = page.query_selector_all(".bp-title")
    hrefs = {href for link in links if (href := link.get_attribute("href"))}
    _update_articles_cache(*hrefs)


def _update_articles_cache(*args: str) -> None:
    """Update the articles cache."""
    BLOG_ARTICLES.update(args)


def get_article_from_cache() -> str:
    """Get an article from the cache at random."""
    return sorted(BLOG_ARTICLES)[0] if BLOG_ARTICLES else ""
