"""conftest: setup file for the functional tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app import PROJECT_ROOT
from app.web import main
from scripts.start_local_postgres import DBBuilder
from tests.functional_tests import BASE_URL

pytestmark = pytest.mark.anyio


class CustomTestClient(TestClient):
    """Custom TestClient for the app."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def get(self, *args, to_file: bool = False, **kwargs) -> httpx.Response:
        """Make a GET request to the app."""
        response = super().get(*args, **kwargs)
        if to_file:  # pragma: no cover
            self._to_file(response)
        return response

    def post(self, *args, to_file: bool = False, **kwargs) -> httpx.Response:
        """Make a POST request to the app."""
        response = super().post(*args, **kwargs)
        if to_file:  # pragma: no cover (only for debugging)
            self._to_file(response)
        return response

    def put(  # pragma: no cover (no PUT routes yet)
        self, *args, to_file: bool = False, **kwargs
    ) -> httpx.Response:
        """Make a PUT request to the app."""
        response = super().put(*args, **kwargs)
        if to_file:  # pragma: no cover (only for debugging)
            self._to_file(response)
        return response

    def patch(self, *args, to_file: bool = False, **kwargs) -> httpx.Response:
        """Make a PATCH request to the app."""
        response = super().patch(*args, **kwargs)
        if to_file:  # pragma: no cover (only for debugging)
            self._to_file(response)
        return response

    def delete(self, *args, to_file: bool = False, **kwargs) -> httpx.Response:
        """Make a DELETE request to the app."""
        response = super().delete(*args, **kwargs)
        if to_file:  # pragma: no cover (only for debugging)
            self._to_file(response)
        return response

    @staticmethod
    def _to_file(response: httpx.Response) -> None:  # pragma: no cover (only for debugging)
        """Write the response to a file."""
        filename = "html_response.html"
        path = PROJECT_ROOT / filename
        path.write_text(response.text)


@pytest.fixture(scope="session", name="test_client")
def test_client_session_fixture(db_builder: DBBuilder) -> TestClient:  # noqa: ARG001 (unused-arg)
    """Return a test client for the app."""
    app = main.create_app()
    return CustomTestClient(app, base_url=BASE_URL)
