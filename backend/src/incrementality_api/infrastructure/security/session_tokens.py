import hashlib
import secrets

from incrementality_api.application.authentication.ports import (
    IssuedSessionToken,
)


class SecureSessionTokenGenerator:
    """Generate secure session tokens and persistent SHA-256 digests."""

    def __init__(self, *, token_bytes: int = 32) -> None:
        if token_bytes < 32:
            raise ValueError("Session tokens require at least 32 random bytes.")

        self._token_bytes = token_bytes

    def issue(self) -> IssuedSessionToken:
        raw_token = secrets.token_urlsafe(
            self._token_bytes,
        )

        return IssuedSessionToken(
            raw_token=raw_token,
            token_hash=self.hash_token(raw_token),
        )

    def hash_token(self, raw_token: str) -> str:
        if not raw_token:
            raise ValueError("Session token cannot be empty.")

        return hashlib.sha256(
            raw_token.encode("utf-8"),
        ).hexdigest()
