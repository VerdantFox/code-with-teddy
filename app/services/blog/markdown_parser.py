"""markdown_parser: service for parsing markdown into HTML."""
import re

from bs4 import BeautifulSoup, Tag
from markdown import Markdown
from markdown.extensions import Extension
from markdown.extensions.admonition import AdmonitionExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension
from markdown.extensions.sane_lists import SaneListExtension
from markdown.extensions.smarty import SmartyExtension
from markdown.extensions.toc import TocExtension
from micawber import bootstrap_basic, parse_html
from micawber.cache import Cache as OEmbedCache
from pydantic import BaseModel

# Configure micawber with the default OEmbed providers (YouTube, etc).
oembed_providers = bootstrap_basic(OEmbedCache())
MAX_MEDIA_WIDTH = 800
HTML_PARSER = "html.parser"


class HTMLContent(BaseModel):
    """Markdown content rendered to HTML."""

    content: str
    toc: str


def markdown_to_html(markdown_content: str) -> HTMLContent:
    """Generate HTML representation of the markdown-formatted blog entry.

    Also convert any media URLs into rich media objects such as video
    players or images.
    """
    extensions: list[str | Extension] = [
        CodeHiliteExtension(linenums=False, css_class="highlight"),
        ExtraExtension(),
        TocExtension(toc_depth=3),
        AdmonitionExtension(),
        SaneListExtension(),
        SmartyExtension(),
        "pymdownx.tilde",
    ]
    md = Markdown(extensions=extensions)
    assert hasattr(md, "toc")  # noqa: S101 (assert) -- for mypy
    html = md.convert(markdown_content)
    html = update_html(html)
    html_with_oembed = parse_html(
        html,
        oembed_providers,
        urlize_all=True,
        maxwidth=MAX_MEDIA_WIDTH,
    )
    return HTMLContent(content=html_with_oembed, toc=update_toc(md.toc))


def update_html(html: str) -> str:
    """Update the blog HTML content."""
    html_soup = BeautifulSoup(html, HTML_PARSER)
    _update_html_links(html_soup)
    _update_html_headers(html_soup)
    _update_html_pre_tags(html_soup)
    _update_html_code_highlights(html_soup)
    _update_html_images(html_soup)
    return str(html_soup)


def _update_html_links(html_soup: BeautifulSoup) -> None:
    """Make all links open in new tab."""
    for a_tag in html_soup.find_all("a"):
        a_tag["target"] = "_blank"
        a_tag["rel"] = "noopener noreferrer"


def _update_html_headers(html_soup: BeautifulSoup) -> None:
    """Fix header IDs that don't start alpha to work with scrollspy."""
    for h_tag in html_soup.find_all(re.compile(r"^h[1-6]$")):
        id_ = h_tag.get("id")
        if h_tag.get("id") and not id_[0].isalpha():
            h_tag["id"] = f"blog-{id_}"
        h_tag["x-intersect"] = f"highlightTocElement('{id_}')"


def _update_html_pre_tags(html_soup: BeautifulSoup) -> None:
    """Make all pre tags tab-to-able (for accessibility)."""
    for pre_tag in html_soup.find_all("pre"):
        pre_tag["tabindex"] = "0"


def _update_html_code_highlights(html_soup: BeautifulSoup) -> None:
    """Add "not-prose" class to all "highlight" code blocks."""
    for code_tag in html_soup.find_all("div", {"class": "highlight"}):
        code_tag["class"].append("not-prose")


def _update_html_images(html_soup: BeautifulSoup) -> None:
    """Make all image paragraphs centered for captions.

    Was also adding loading="lazy" to images, but it made table of contents
    jump to wrong places until the images were properly loaded.
    """
    for img in html_soup.find_all("img"):
        if img.parent.name != "p":
            continue
        img.parent["class"] = "text-center"
    for picture in html_soup.find_all("picture"):
        picture.parent["class"] = "text-center"


def update_toc(toc: str) -> str:
    """Update the table of contents HTML."""
    toc_soup = BeautifulSoup(toc, HTML_PARSER)
    toc_element = toc_soup.find("div", {"class": "toc"})
    update_element(
        element=toc_element,
        name="nav",
        id_="toc",
        class_="not-prose",
    )
    toc_list_outer = toc_element.find("ul")
    update_element(
        element=toc_list_outer,
        class_="flex flex-col gap-4",
    )
    for li_tag in toc_list_outer.find_all("li"):
        update_element(
            element=li_tag,
            class_="flex flex-col gap-4",
        )
        a_tag = li_tag.find("a")
        update_element(
            element=a_tag,
            class_="link px-2 py-1 rounded-lg",
        )
        ul_tags = li_tag.find_all("ul")
        for ul_tag in ul_tags:
            update_element(
                element=ul_tag,
                class_="flex flex-col gap-4 ml-6",
            )

        update_a_tag_alpha_href(a_tag)
    # Add title comments and contact sections
    title = BeautifulSoup(
        '<a class="link" href="#">Title</a>',
        HTML_PARSER,
    )
    toc_list_outer.insert(0, title)
    about = BeautifulSoup(
        '<a class="link" href="#about-the-author">About the author</a>',
        HTML_PARSER,
    )
    comments = BeautifulSoup(
        '<a class="link" href="#comments-section">Comments</a>',
        HTML_PARSER,
    )
    toc_list_outer.extend([about, comments])
    return str(toc_soup)


def update_element(
    *,
    element: BeautifulSoup,
    name: str | None = None,
    id_: str | None = None,
    class_: str | None = None,
) -> None:
    """Update an element's name and class."""
    if name:
        element.name = name
    if class_:
        element["class"] = class_
    if id_:
        element["id"] = id_


def hoist_children_to_parent(element: Tag) -> list[Tag]:
    """Hoist all children of element to parent element."""
    parent = element.parent
    children = element.find_all(recursive=False)
    parent.extend(children)
    element.decompose()
    return children


def update_a_tag_alpha_href(a_tag: Tag) -> None:
    """Update a tag ID if not alpha.

    Scrollspy fails when the ID does not begin with a letter [a-zA-Z].
    Fix by adding a prefix to the ID of the element and the TOC link
    if the ID does not begin with a letter.
    """
    if a_tag["href"].startswith("#") and not a_tag["href"][1].isalpha():
        a_tag["href"] = f"#blog-{a_tag['href'][1:]}"
