"""conftest: setup file for the functional tests."""

import pytest
from fastapi.testclient import TestClient

from app.web import main
from scripts.start_local_postgres import DBBuilder


@pytest.fixture(scope="session")
def test_client(db_builder: DBBuilder) -> TestClient:  # noqa: ARG001 (unused-arg)
    """Return a test client for the app."""
    app = main.create_app()
    return TestClient(app)
