from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from incrementality_api.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """
    Create one database session for one request.

    Sessions must not be shared between concurrent requests or tasks.
    """

    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session
