from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.authentication.errors import (
    InvalidCredentialsError,
)
from incrementality_api.application.authentication.login import (
    Login,
    LoginCommand,
)
from incrementality_api.infrastructure.database.models.authentication import (
    AuthSessionModel,
    UserCredentialModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    UserModel,
)
from incrementality_api.infrastructure.database.unit_of_work.authentication import (
    SqlAlchemyAuthenticationUnitOfWork,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)
from incrementality_api.infrastructure.security.session_tokens import (
    SecureSessionTokenGenerator,
)

FIXED_NOW = datetime(
    2026,
    7,
    13,
    18,
    0,
    tzinfo=UTC,
)

PASSWORD = "Correct-password-123!"


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


async def seed_user_with_credential(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "owner@example.com",
    password: str = PASSWORD,
) -> UUID:
    user_id = uuid4()
    password_hash = Argon2PasswordHasher().hash(password)

    async with session_factory() as session, session.begin():
        session.add(
            UserModel(
                id=user_id,
                email=email,
                display_name="Tina Rincon",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

        session.add(
            UserCredentialModel(
                user_id=user_id,
                password_hash=password_hash,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

    return user_id


async def count_sessions(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(
                AuthSessionModel,
            )
        )

    return int(count or 0)


@pytest.mark.asyncio
async def test_login_persists_only_session_token_hash(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id = await seed_user_with_credential(
        tenancy_session_factory,
    )

    token_generator = SecureSessionTokenGenerator()

    service = Login(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        password_hasher=Argon2PasswordHasher(),
        token_generator=token_generator,
        clock=FixedClock(),
        session_lifetime=timedelta(hours=8),
    )

    result = await service.execute(
        LoginCommand(
            email="  OWNER@EXAMPLE.COM  ",
            password=PASSWORD,
        )
    )

    assert result.user_id == user_id
    assert result.raw_session_token
    assert result.expires_at == (FIXED_NOW + timedelta(hours=8))

    async with tenancy_session_factory() as session:
        stored_session = await session.scalar(select(AuthSessionModel))

    assert stored_session is not None
    assert stored_session.user_id == user_id
    assert stored_session.token_hash != (result.raw_session_token)
    assert stored_session.token_hash == (
        token_generator.hash_token(
            result.raw_session_token,
        )
    )
    assert stored_session.created_at == FIXED_NOW
    assert stored_session.expires_at == result.expires_at
    assert stored_session.revoked_at is None


@pytest.mark.asyncio
async def test_wrong_password_does_not_persist_session(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await seed_user_with_credential(
        tenancy_session_factory,
    )

    service = Login(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        password_hasher=Argon2PasswordHasher(),
        token_generator=SecureSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await service.execute(
            LoginCommand(
                email="owner@example.com",
                password="Wrong-password-456!",
            )
        )

    assert (
        await count_sessions(
            tenancy_session_factory,
        )
        == 0
    )


@pytest.mark.asyncio
async def test_unknown_email_does_not_persist_session(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = Login(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        password_hasher=Argon2PasswordHasher(),
        token_generator=SecureSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await service.execute(
            LoginCommand(
                email="missing@example.com",
                password="Any-password-123!",
            )
        )

    assert (
        await count_sessions(
            tenancy_session_factory,
        )
        == 0
    )
