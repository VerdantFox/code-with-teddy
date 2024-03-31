"""test_users_mutating: mutating tests for the users API routes."""

import pytest


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""
