"""database: database connection and dependency."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.settings import settings

# connect_args={"check_same_thread": False} for SQLite

ENGINE: AsyncEngine | None = None
SESSION_MAKER: async_sessionmaker[AsyncSession] | None = None


def get_engine(
    *,
    connection_string: str | None = None,
    echo: bool | None = None,
    pool_size: int | None = None,
    new: bool = False,
) -> AsyncEngine:
    """Return the database engine, creating a new one if needed."""
    global ENGINE, SESSION_MAKER  # noqa: PLW0603 (global-statement)
    if not new and ENGINE is not None:
        return ENGINE

    connection_string = connection_string or settings.db_connection_string
    echo = echo if echo is not None else settings.db_echo
    pool_size = pool_size if pool_size is not None else settings.db_pool_size
    ENGINE = create_async_engine(
        connection_string,
        echo=echo,
        pool_size=pool_size,
        pool_pre_ping=True,
    )
    SESSION_MAKER = None  # reset when engine changes
    return ENGINE


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the async session maker, creating a new one if needed."""
    global SESSION_MAKER  # noqa: PLW0603 (global-statement)
    if SESSION_MAKER is None:
        SESSION_MAKER = async_sessionmaker(get_engine(), expire_on_commit=False)
    return SESSION_MAKER


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Start a SessionLocal transaction and yield it."""
    async with get_session_maker()() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db_session)]
