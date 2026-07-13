from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.authentication.entities import (
    AuthSession,
    PasswordCredential,
)


@dataclass(frozen=True, slots=True)
class IssuedSessionToken:
    """
    A raw session token and its persistent digest.

    The raw token is returned once to the client.
    Only the token hash is stored in PostgreSQL.
    """

    raw_token: str
    token_hash: str


@dataclass(frozen=True, slots=True)
class LoginUser:
    id: UUID
    email: str


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str:
        """Create a secure password hash."""

    def verify(
        self,
        *,
        password_hash: str,
        password: str,
    ) -> bool:
        """Return whether the password matches the stored hash."""

    def needs_rehash(self, password_hash: str) -> bool:
        """Return whether current parameters require a new hash."""


class SessionTokenGenerator(Protocol):
    def issue(self) -> IssuedSessionToken:
        """Generate a raw session token and persistent digest."""

    def hash_token(self, raw_token: str) -> str:
        """Create the persistent digest for a raw token."""


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware time."""


class LoginUserRepository(Protocol):
    async def get_by_email(
        self,
        email: str,
    ) -> LoginUser | None:
        """Find a login identity by normalized email."""


class CredentialRepository(Protocol):
    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> PasswordCredential | None:
        """Find the password credential belonging to a user."""


class AuthSessionRepository(Protocol):
    async def add(self, session: AuthSession) -> None:
        """Persist an authentication session."""


class AuthenticationUnitOfWork(Protocol):
    users: LoginUserRepository
    credentials: CredentialRepository
    sessions: AuthSessionRepository

    async def __aenter__(
        self,
    ) -> "AuthenticationUnitOfWork":
        """Begin the authentication transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commit cleanup or roll back after an exception."""

    async def commit(self) -> None:
        """Commit the authentication transaction."""

    async def rollback(self) -> None:
        """Roll back the authentication transaction."""


class SessionTokenHasher(Protocol):
    def hash_token(self, raw_token: str) -> str:
        """Create the persistent digest for a raw session token."""


class SessionRepository(Protocol):
    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthSession | None:
        """Find a session by its persistent token digest."""

    async def save(self, session: AuthSession) -> None:
        """Persist changes to an existing session."""


class SessionUnitOfWork(Protocol):
    sessions: SessionRepository

    async def __aenter__(
        self,
    ) -> "SessionUnitOfWork":
        """Begin the session transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit the session transaction."""

    async def rollback(self) -> None:
        """Roll back the session transaction."""
