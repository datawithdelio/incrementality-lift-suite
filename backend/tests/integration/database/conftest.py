import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    ("postgresql+asyncpg://incrementality:incrementality@localhost:55432/incrementality_test"),
)

_TEST_ENGINE = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

_TEST_SESSION_FACTORY = async_sessionmaker(
    bind=_TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def truncate_tenancy_tables() -> None:
    async with _TEST_ENGINE.begin() as connection:
        await connection.execute(
            text(
                """
                TRUNCATE TABLE
                    auth_sessions,
                    user_credentials,
                    projects,
                    workspace_memberships,
                    workspaces,
                    users,
                    organizations
                CASCADE
                """
            )
        )


@pytest_asyncio.fixture
async def tenancy_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    await truncate_tenancy_tables()

    yield _TEST_SESSION_FACTORY

    await truncate_tenancy_tables()
