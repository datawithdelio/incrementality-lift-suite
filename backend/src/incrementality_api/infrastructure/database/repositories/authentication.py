from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.authentication.ports import (
    LoginUser,
)
from incrementality_api.domain.authentication.entities import (
    AuthSession,
    PasswordCredential,
)
from incrementality_api.infrastructure.database.models.authentication import (
    AuthSessionModel,
    UserCredentialModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    UserModel,
)


class SqlAlchemyLoginUserRepository:
    """Read login identities from PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(
        self,
        email: str,
    ) -> LoginUser | None:
        statement = select(UserModel).where(
            UserModel.email == email,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return LoginUser(
            id=model.id,
            email=model.email,
        )


class SqlAlchemyCredentialRepository:
    """Read password credentials from PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> PasswordCredential | None:
        statement = select(UserCredentialModel).where(
            UserCredentialModel.user_id == user_id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return PasswordCredential(
            user_id=model.user_id,
            password_hash=model.password_hash,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyAuthSessionRepository:
    """Persist and retrieve authentication sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: AuthSession) -> None:
        model = AuthSessionModel(
            id=session.id,
            user_id=session.user_id,
            token_hash=session.token_hash,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
        )

        self._session.add(model)
        await self._session.flush()

    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthSession | None:
        statement = select(AuthSessionModel).where(
            AuthSessionModel.token_hash == token_hash,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return AuthSession(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            created_at=model.created_at,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )

    async def save(self, session: AuthSession) -> None:
        statement = select(AuthSessionModel).where(
            AuthSessionModel.id == session.id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            raise RuntimeError("Cannot update an authentication session that does not exist.")

        model.user_id = session.user_id
        model.token_hash = session.token_hash
        model.created_at = session.created_at
        model.expires_at = session.expires_at
        model.revoked_at = session.revoked_at

        await self._session.flush()
