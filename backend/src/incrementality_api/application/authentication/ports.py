from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IssuedSessionToken:
    """
    A raw session token and its persistent digest.

    raw_token:
        Returned once to the authenticated client.

    token_hash:
        Stored in PostgreSQL instead of the usable raw token.
    """

    raw_token: str
    token_hash: str


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
        """Generate a new raw session token and persistent digest."""

    def hash_token(self, raw_token: str) -> str:
        """Create the persistent digest for a raw token."""
