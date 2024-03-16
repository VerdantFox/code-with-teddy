"""conftest: setup file for the functional html tests."""

from collections.abc import Callable

import httpx
import pytest

from app import PROJECT_ROOT


@pytest.fixture(scope="session")
def html_to_file() -> Callable[[httpx.Response, str | None], None]:  # pragma: no cover
    """Write the html response to a file."""

    def _html_to_file(response: httpx.Response, filename: str | None = None) -> None:
        """Write the html response to a file."""
        if filename is None:
            filename = "html_response.html"
        path = PROJECT_ROOT / filename
        path.write_text(response.text)

    return _html_to_file
