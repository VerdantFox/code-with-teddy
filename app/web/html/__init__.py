"""const: Constants for the HTML web package."""

from pathlib import Path

import jinja_partials
from fastapi.templating import Jinja2Templates

html = Path(__file__).parent.parent / "html"
TEMPLATES_DIR = html / "templates"
STATIC_DIR = html / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
jinja_partials.register_starlette_extensions(templates)
