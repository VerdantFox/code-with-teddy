"""conftest: setup file for pytest root."""

from collections.abc import AsyncGenerator
from os import getenv
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy_utils.functions import database_exists, drop_database

from app.datastore.database import get_engine
from app.services.general.transforms import to_bool
from scripts.start_local_postgres import DBBuilder

load_dotenv()


# ------------------------ Postgres vars ------------------------
TEST_DB_CONTAINER_NAME = getenv("TEST_DB_CONTAINER_NAME", "postgres_test")
TEST_DB_HOST = getenv("TEST_DB_HOST", "localhost")
TEST_DB_USERNAME = getenv("TEST_DB_USERNAME", "pytest_user")
TEST_DB_PASSWORD = getenv("TEST_DB_PASSWORD", "pytest_pw")
TEST_DB_NAME = getenv("TEST_DB_NAME", "pytest_db")
TEST_DB_PORT = int(getenv("TEST_DB_PORT", "5433"))

# ---------------------- Other vars ----------------------
# don't tear down the postgres container after tests
CONTAINER_NO_TEARDOWN = to_bool(getenv("CONTAINER_NO_TEARDOWN", "false"))


# ---------------------------------------------------------------------------
# Pytest magic functions
# ---------------------------------------------------------------------------
def pytest_addoption(parser: pytest.Parser) -> None:
    """Add option to run playwright tests."""
    environments = ["LOCAL", "PROD"]
    help_msg = (
        "Run API integration tests against the specified environment. Options:" f" {environments}"
    )
    parser.addoption("--integration", action="store", help=help_msg)
    help_msg = (
        "Run UI playwright tests against the specified environment. Options:" f" {environments}"
    )
    parser.addoption("--playwright", action="store", help=help_msg)


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    """Return True to prevent considering this path for collection.

    - `--integration`: run `api_tests`
    - `--playwright`: run `playwright_tests`
    - not specified: run all non-integration tests
    """
    run_integration = bool(config.getoption("--integration"))
    if "integration_tests" in collection_path.parts:
        return not run_integration
    run_playwright = bool(config.getoption("--playwright"))
    if "playwright_tests" in collection_path.parts:
        return not run_playwright
    return run_integration or run_playwright


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(name="db_builder", scope="session")
async def generate_postgres_container() -> AsyncGenerator[DBBuilder, None]:
    """Generate a fresh test postgres container for the duration of the test session."""
    db_builder = DBBuilder(
        container_name=TEST_DB_CONTAINER_NAME,
        username=TEST_DB_USERNAME,
        password=TEST_DB_PASSWORD,
        database=TEST_DB_NAME,
        port=TEST_DB_PORT,
        teardown=True,
        create_db=True,
        migration_version=None,
        populate=False,
        silent=True,
    )
    pg_container = await db_builder.main()
    db_url = db_builder.get_connection_string()
    assert database_exists(db_url)
    yield db_builder
    if CONTAINER_NO_TEARDOWN:  # pragma: no cover
        return
    drop_database(db_url)
    assert not database_exists(db_url)
    pg_container.stop()
    pg_container.remove()


@pytest.fixture(name="db_session")
async def get_db_session(db_builder: DBBuilder) -> AsyncGenerator[AsyncSession, None]:
    """Return the test db session and clean up after by deleting all table data."""
    async_session = make_session(db_builder)
    async with async_session() as session:
        yield session
        await delete_all_data(session, db_builder)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def make_session(db_builder: DBBuilder) -> async_sessionmaker[AsyncSession]:
    """Create a new async session."""
    connection_string = db_builder.get_connection_string()
    db_echo: bool = False
    db_pool_size: int = 5
    engine = get_engine(
        new=True, connection_string=connection_string, echo=db_echo, pool_size=db_pool_size
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def delete_all_data(session: AsyncSession, db_builder: DBBuilder) -> None:
    """Delete all data from the database."""
    # Delete data from all tables
    for table in reversed(db_builder.metadata.sorted_tables):
        await session.execute(delete(table))
    # Commit the transaction
    await session.commit()
