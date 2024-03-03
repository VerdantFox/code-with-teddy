"""const: Constants for the HTML web package."""

import textwrap
from pathlib import Path

import jinja_partials
from fastapi.templating import Jinja2Templates

html = Path(__file__).parent.parent / "html"
TEMPLATES_DIR = html / "templates"
STATIC_DIR = html / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
jinja_partials.register_starlette_extensions(templates)


def shorten(
    text: str, width: int = 150, placeholder: str = "...", replace_newline: str | None = None
) -> str:
    """Shorten the text to the given length."""
    if replace_newline:
        text = text.replace("\n", replace_newline)
    return textwrap.shorten(text, width=width, placeholder=placeholder)


templates.env.globals["shorten"] = shorten
