"""conftest: setup file for pytest root."""

from collections.abc import AsyncGenerator, Iterable
from os import getenv
from pathlib import Path

import pytest
import sqlalchemy as sa
from dotenv import load_dotenv
from pytest_mock import MockerFixture
from sqlalchemy import Table, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy_utils.functions import database_exists

from app.datastore import database as db_module
from app.datastore.database import get_engine
from app.services.general.transforms import to_bool
from scripts.start_local_postgres import DBBuilder
from tests import ADMIN_COOKIE, ADMIN_TOKEN, BASIC_COOKIE, BASIC_TOKEN

load_dotenv()
pytestmark = pytest.mark.anyio

# --------------------- Postgres vars -------------------
TEST_DB_CONTAINER_NAME = getenv("TEST_DB_CONTAINER_NAME", "postgres_test")
TEST_DB_HOST = getenv("TEST_DB_HOST", "localhost")
TEST_DB_USERNAME = getenv("TEST_DB_USERNAME", "pytest_user")
TEST_DB_PASSWORD = getenv("TEST_DB_PASSWORD", "pytest_pw")
TEST_DB_NAME = getenv("TEST_DB_NAME", "pytest_db")
TEST_DB_PORT = int(getenv("TEST_DB_PORT", "5433"))

# ---------------------- Other vars ---------------------
# don't tear down the postgres container after tests
CONTAINER_NO_TEARDOWN = to_bool(getenv("CONTAINER_NO_TEARDOWN", "false"))


# ---------------- Load plugin fixtures -----------------
pytest_plugins = ["tests.model_fixtures"]


# -------------------------------------------------------
# Pytest magic functions
# -------------------------------------------------------
def pytest_addoption(parser: pytest.Parser) -> None:
    """Add option to run playwright tests."""
    environments = ["local", "prod"]
    help_msg = (
        f"Run API integration tests against the specified environment. Options: {environments}"
    )
    parser.addoption("--integration", action="store", help=help_msg)
    help_msg = f"Run UI playwright tests against the specified environment. Options: {environments}"
    parser.addoption("--playwright", action="store", help=help_msg)
    help_msg = "Run all tests including integration and playwright end-to-end tests."
    parser.addoption("--all", action="store_true", help=help_msg)


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    """Return True to prevent considering this path for collection.

    - `--all`: run all tests (against local environment)
    - `--integration=ENV`: only run integration tests (against ENV environment)
    - `--playwright=ENV`: only run playwright end-to-end tests (against ENV environment)
    - not specified: only run all unit/functional tests
    """
    if config.getoption("--all"):
        return False
    run_integration = bool(config.getoption("--integration"))
    if "integration_tests" in collection_path.parts:
        return not run_integration
    run_playwright = bool(config.getoption("--playwright"))
    if "playwright_tests" in collection_path.parts:
        return not run_playwright
    return run_integration or run_playwright


# -------------------------------------------------------
# Fixtures
# -------------------------------------------------------
@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Return the anyio backend to use as a session scoped fixture."""
    return "asyncio"


@pytest.fixture(name="db_builder", scope="session")
async def generate_postgres_container() -> AsyncGenerator[DBBuilder]:
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
    # Dispose the async engine pool to release all connections before dropping the DB
    if db_module.ENGINE is not None:
        await db_module.ENGINE.dispose()
    # Use WITH (FORCE) to terminate remaining sessions and drop (PostgreSQL 13+)
    admin_url = db_url.rsplit("/", 1)[0] + "/postgres"
    sync_engine = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with sync_engine.connect() as conn:
        conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
    sync_engine.dispose()
    assert not database_exists(db_url)
    pg_container.stop()
    pg_container.remove()


# ------------------ Session fixtures -------------------
@pytest.fixture(name="session_maker", scope="session")
def get_session_maker(db_builder: DBBuilder) -> async_sessionmaker[AsyncSession]:
    """Return a single session-scoped async session maker (one engine for the whole run)."""
    return _make_session(db_builder)


@pytest.fixture(name="db_session")
async def get_db_session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Return the test db session."""
    async with session_maker() as session:
        yield session


@pytest.fixture(name="db_session_module", scope="module")
async def get_db_session_module(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Return the test db session."""
    async with session_maker() as session:
        yield session


# --------------- Mock external services ----------------
# Email service
@pytest.fixture(name="mock_mailersend", autouse=True, scope="session")
def _mock_mailersend(session_mocker: MockerFixture) -> None:
    """Mock the mailersend email service."""
    session_mocker.patch("app.services.general.email_handler.MailerSendClient")


# ----------------- Clean DB fixtures -------------------
@pytest.fixture(name="clean_db")
async def _clean_db_function(
    db_session: AsyncSession, db_builder: DBBuilder
) -> AsyncGenerator[None]:
    """Delete all data from the database after the function."""
    yield
    await delete_all_data(db_session, db_builder)
    _clear_tokens()


@pytest.fixture(name="clean_db_except_users")
async def _clean_db_except_users(
    db_session: AsyncSession, db_builder: DBBuilder
) -> AsyncGenerator[None]:
    """Delete all data from the database except users after the function."""
    yield
    await delete_all_data(db_session, db_builder, skip_tables={"users"})


@pytest.fixture(name="clean_db_module", scope="module")
async def _clean_db_module(
    db_session_module: AsyncSession, db_builder: DBBuilder
) -> AsyncGenerator[None]:
    """Delete all data from the database after the module."""
    yield
    await delete_all_data(db_session_module, db_builder)
    _clear_tokens()


# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------
def _make_session(db_builder: DBBuilder) -> async_sessionmaker[AsyncSession]:
    """Create a new async session maker backed by a single engine."""
    connection_string = db_builder.get_connection_string()
    engine = get_engine(new=True, connection_string=connection_string, echo=False, pool_size=5)
    return async_sessionmaker(engine, expire_on_commit=False)


async def delete_all_data(
    session: AsyncSession, db_builder: DBBuilder, skip_tables: Iterable[str] | None = None
) -> None:
    """Delete all data from the database."""
    tables: Iterable[Table] = reversed(db_builder.metadata.sorted_tables)
    if skip_tables:
        tables = [table for table in tables if table.name not in skip_tables]
    # Delete data from all tables
    for table in tables:
        await session.execute(delete(table))
    # Commit the transaction
    await session.commit()


def _clear_tokens() -> None:
    """Clear token caches."""
    BASIC_COOKIE.clear()
    ADMIN_COOKIE.clear()
    BASIC_TOKEN.clear()
    ADMIN_TOKEN.clear()
