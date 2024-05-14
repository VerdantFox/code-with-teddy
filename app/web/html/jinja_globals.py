"""jinja_globals: Jinja2 globals for the HTML web package.

Adds custom Jinja2 globals to the templates environment.
"""

import textwrap
from urllib.parse import quote

from app.services.blog.blog_utils import strip_markdown
from app.settings import settings
from app.web.html import flash_messages
from app.web.html.const import templates


def shorten(
    text: str,
    *,
    width: int = 150,
    placeholder: str = "...",
    urlencode: bool = False,
    stop_at_newline: bool = True,
) -> str:
    """Shorten the text to the given length."""
    if stop_at_newline:
        text = text.split("\n")[0]
    text = textwrap.shorten(text, width=width, placeholder=placeholder)
    if urlencode:
        text = quote(text)
    return text


templates.env.globals["abs"] = abs
templates.env.globals["hasattr"] = hasattr
templates.env.globals["shorten"] = shorten
templates.env.globals["strip_markdown"] = strip_markdown
templates.env.globals["get_flashed_messages"] = flash_messages.get_flashed_messages
templates.env.globals["sentry_cdn"] = settings.sentry_cdn
