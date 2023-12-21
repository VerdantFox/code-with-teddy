"""database: database connection and dependency."""
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.settings import settings

# connect_args={"check_same_thread": False} for SQLite

engine = create_engine(
    settings.db_connection_string,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Start a SessionLocal transaction and yield it."""
    with SessionLocal.begin() as session:
        yield session


DBSession = Annotated[Session, Depends(get_db_session)]
