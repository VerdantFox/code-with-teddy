"""const: Constants for the HTML web package."""

import textwrap
from pathlib import Path
from urllib.parse import quote

import jinja_partials
from fastapi.templating import Jinja2Templates

from app.services.blog.blog_utils import strip_markdown

html = Path(__file__).parent.parent / "html"
TEMPLATES_DIR = html / "templates"
STATIC_DIR = html / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
jinja_partials.register_starlette_extensions(templates)


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


templates.env.globals["shorten"] = shorten
templates.env.globals["abs"] = abs
templates.env.globals["strip_markdown"] = strip_markdown
