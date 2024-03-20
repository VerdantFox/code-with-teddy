"""conftest: setup file for pytest root."""

from collections.abc import AsyncGenerator
from os import getenv
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy_utils.functions import database_exists, drop_database

from app.datastore import db_models
from app.datastore.database import get_engine
from app.services.blog import blog_handler
from app.services.general.transforms import to_bool
from scripts.start_local_postgres import DBBuilder
from tests.data import models as test_models
from tests.functional_tests.html_tests.const import ADMIN_COOKIE, BASIC_COOKIE

load_dotenv()
pytestmark = pytest.mark.anyio

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
@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Return the anyio backend to use as a session scoped fixture."""
    return "asyncio"


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
    """Return the test db session."""
    async_session = _make_session(db_builder)
    async with async_session() as session:
        yield session


@pytest.fixture(name="db_session_module", scope="module")
async def get_db_session_module(db_builder: DBBuilder) -> AsyncGenerator[AsyncSession, None]:
    """Return the test db session."""
    async_session = _make_session(db_builder)
    async with async_session() as session:
        yield session


@pytest.fixture(name="clean_db_function")
async def _clean_db_function(
    db_session: AsyncSession, db_builder: DBBuilder
) -> AsyncGenerator[None, None]:
    """Delete all data from the database after the function."""
    yield
    await _delete_all_data(db_session, db_builder)
    _clear_cookies()


@pytest.fixture(name="clean_db_module", scope="module")
async def _clean_db_module(
    db_session_module: AsyncSession, db_builder: DBBuilder
) -> AsyncGenerator[None, None]:
    """Delete all data from the database after the module."""
    yield
    await _delete_all_data(db_session_module, db_builder)
    _clear_cookies()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _make_session(db_builder: DBBuilder) -> async_sessionmaker[AsyncSession]:
    """Create a new async session."""
    connection_string = db_builder.get_connection_string()
    db_echo: bool = False
    db_pool_size: int = 5
    engine = get_engine(
        new=True, connection_string=connection_string, echo=db_echo, pool_size=db_pool_size
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def _delete_all_data(session: AsyncSession, db_builder: DBBuilder) -> None:
    """Delete all data from the database."""
    # Delete data from all tables
    for table in reversed(db_builder.metadata.sorted_tables):
        await session.execute(delete(table))
    # Commit the transaction
    await session.commit()


def _clear_cookies() -> None:
    """Clear cookies from the test client."""
    BASIC_COOKIE.clear()
    ADMIN_COOKIE.clear()


# ---------------------------------------------------------------------------
# model fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(name="basic_user")
async def add_basic_user(db_session: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, function scoped."""
    user = test_models.basic_user()
    await add_user(db_session, user)
    return user


@pytest.fixture(name="basic_user_2")
async def add_basic_user_2(db_session: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, function scoped."""
    user = test_models.basic_user(
        username="test_user_2", email="test2@email.com", full_name="Test User 2"
    )
    await add_user(db_session, user)
    return user


@pytest.fixture(name="basic_user_module", scope="module")
async def add_basic_user_module(db_session_module: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, module scoped."""
    user = test_models.basic_user()
    await add_user(db_session_module, user)
    return user


@pytest.fixture(name="admin_user")
async def add_admin_user(db_session: AsyncSession) -> db_models.User:
    """Return an admin user added to the database, function scoped."""
    user = test_models.admin_user()
    await add_user(db_session, user)
    return user


@pytest.fixture(name="admin_user_module", scope="module")
async def add_admin_user_module(db_session_module: AsyncSession) -> db_models.User:
    """Return an admin user added to the database, module scoped."""
    user = test_models.admin_user()
    await add_user(db_session_module, user)
    return user


async def add_user(db_session: AsyncSession, user: db_models.User) -> db_models.User:
    """Add a user to the database."""
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(name="basic_blog_post")
async def add_basic_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Return a basic blog post added to the database."""
    blog_post_input: blog_handler.SaveBlogInput = test_models.basic_blog_post()
    response = await blog_handler.save_blog_post(db=db_session, data=blog_post_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="basic_blog_post_module", scope="module")
async def add_basic_blog_post_module(db_session_module: AsyncSession) -> db_models.BlogPost:
    """Return a basic blog post added to the database."""
    blog_post_input: blog_handler.SaveBlogInput = test_models.basic_blog_post(
        title="Module Blog Post"
    )
    response = await blog_handler.save_blog_post(db=db_session_module, data=blog_post_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="unpublished_blog_post")
async def add_unpublished_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Return an unpublished blog post added to the database."""
    bp_input = test_models.basic_blog_post(is_published=False, title="Unpublished Blog Post")
    response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(scope="module", name="unpublished_blog_post_module")
async def add_unpublished_blog_post_module(db_session_module: AsyncSession) -> db_models.BlogPost:
    """Return an unpublished blog post added to the database."""
    bp_input = test_models.basic_blog_post(is_published=False, title="Unpublished Blog Post")
    response = await blog_handler.save_blog_post(db=db_session_module, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="blog_post_cannot_comment")
async def add_blog_post_cannot_comment(db_session: AsyncSession) -> db_models.BlogPost:
    """Return a blog post that cannot be commented on, added to the database."""
    bp_input = test_models.basic_blog_post(can_comment=False, title="Cannot Comment Blog Post")
    response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="blog_post_cannot_comment_module", scope="module")
async def add_blog_post_cannot_comment_module(
    db_session_module: AsyncSession,
) -> db_models.BlogPost:
    """Return a blog post that cannot be commented on, added to the database."""
    bp_input = test_models.basic_blog_post(can_comment=False, title="Cannot Comment Blog Post")
    response = await blog_handler.save_blog_post(db=db_session_module, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="advanced_blog_post")
async def add_advanced_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Return an advanced blog post added to the database."""
    return await save_advanced_blog_post(db_session)


@pytest.fixture(name="advanced_blog_post_module", scope="module")
async def add_advanced_blog_post_module(db_session_module: AsyncSession) -> db_models.BlogPost:
    """Return an advanced blog post added to the database."""
    return await save_advanced_blog_post(db_session_module)


async def save_advanced_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Save an advanced blog post to the database."""
    bp_input = test_models.advanced_blog_post()
    bp_response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
    bp = bp_response.blog_post
    assert bp
    await blog_handler.commit_media_to_db(
        db=db_session,
        blog_post=bp,
        name="Some media",
        locations_str="some_location.png",
        media_type="image/png",
    )
    comment_input = blog_handler.SaveCommentInput(
        bp_id=bp.id,
        guest_id="guest_id_1",
        name="Guest 1",
        email="guest1@email.com",
        content="Some comment",
    )
    comment_response = await blog_handler.save_new_comment(db=db_session, data=comment_input)
    assert comment_response.comment
    return bp


@pytest.fixture(name="several_blog_posts")
async def add_several_blog_posts(db_session: AsyncSession) -> list[db_models.BlogPost]:
    """Return several blog posts added to the database, function scoped."""
    return await _add_several_blog_posts(db_session)


@pytest.fixture(name="several_blog_posts_module", scope="module")
async def add_several_blog_posts_module(
    db_session_module: AsyncSession,
) -> list[db_models.BlogPost]:
    """Return several blog posts added to the database, module scoped."""
    return await _add_several_blog_posts(db_session_module)


async def _add_several_blog_posts(db_session: AsyncSession) -> list[db_models.BlogPost]:
    """Return several blog posts added to the database."""
    blog_post_inputs = [
        test_models.basic_blog_post(
            title=f"basic_{i}",
            tags=[f"foo_{i+j}" for j in range(3)],
            content=f"test blog post {i}. " * i,
            likes=i,
            views=i * 10,
        )
        for i in range(1, 5)
    ]
    blog_post_inputs[1].is_published = False
    blog_posts = []
    for bp_input in blog_post_inputs:
        response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
        assert response.blog_post
        blog_posts.append(response.blog_post)
    return blog_posts
