from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.logout import (
    Logout,
)
from incrementality_api.application.authentication.validate_session import (
    ValidateSession,
)
from incrementality_api.infrastructure.database.models.authentication import (
    AuthSessionModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    UserModel,
)
from incrementality_api.infrastructure.database.unit_of_work.authentication import (
    SqlAlchemyAuthenticationUnitOfWork,
)
from incrementality_api.infrastructure.security.session_tokens import (
    SecureSessionTokenGenerator,
)

FIXED_NOW = datetime(
    2026,
    7,
    13,
    20,
    0,
    tzinfo=UTC,
)

RAW_TOKEN = "persistent-session-token"


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


async def seed_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    raw_token: str = RAW_TOKEN,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> tuple[UUID, UUID]:
    user_id = uuid4()
    session_id = uuid4()

    token_hash = SecureSessionTokenGenerator().hash_token(
        raw_token,
    )

    created = created_at or (FIXED_NOW - timedelta(hours=1))

    expires = expires_at or (FIXED_NOW + timedelta(hours=7))

    async with (
        session_factory() as database_session,
        database_session.begin(),
    ):
        database_session.add(
            UserModel(
                id=user_id,
                email=f"{user_id}@example.com",
                display_name="Session User",
                created_at=created,
                updated_at=created,
            )
        )

        await database_session.flush()

        database_session.add(
            AuthSessionModel(
                id=session_id,
                user_id=user_id,
                token_hash=token_hash,
                created_at=created,
                expires_at=expires,
                revoked_at=revoked_at,
            )
        )

    return session_id, user_id


@pytest.mark.asyncio
async def test_validate_session_loads_identity_from_postgres(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_id, user_id = await seed_session(
        tenancy_session_factory,
    )

    service = ValidateSession(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        token_hasher=SecureSessionTokenGenerator(),
        clock=FixedClock(),
    )

    result = await service.execute(RAW_TOKEN)

    assert result.session_id == session_id
    assert result.user_id == user_id
    assert result.expires_at == (FIXED_NOW + timedelta(hours=7))


@pytest.mark.asyncio
async def test_validate_session_rejects_expired_database_session(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await seed_session(
        tenancy_session_factory,
        created_at=FIXED_NOW - timedelta(hours=9),
        expires_at=FIXED_NOW - timedelta(hours=1),
    )

    service = ValidateSession(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        token_hasher=SecureSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidSessionTokenError,
        match="Invalid or expired session",
    ):
        await service.execute(RAW_TOKEN)


@pytest.mark.asyncio
async def test_logout_persists_revocation(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session_id, _ = await seed_session(
        tenancy_session_factory,
    )

    service = Logout(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        token_hasher=SecureSessionTokenGenerator(),
        clock=FixedClock(),
    )

    await service.execute(RAW_TOKEN)

    async with tenancy_session_factory() as database_session:
        stored = await database_session.scalar(
            select(AuthSessionModel).where(
                AuthSessionModel.id == session_id,
            )
        )

    assert stored is not None
    assert stored.revoked_at == FIXED_NOW


@pytest.mark.asyncio
async def test_logout_rejects_unknown_database_session(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = Logout(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        token_hasher=SecureSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidSessionTokenError,
        match="Invalid or expired session",
    ):
        await service.execute("unknown-session-token")
