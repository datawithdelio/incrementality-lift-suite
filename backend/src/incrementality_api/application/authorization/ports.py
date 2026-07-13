from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.tenancy.entities import (
    WorkspaceMembership,
)


class WorkspaceMembershipReader(Protocol):
    async def get_by_workspace_and_user(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None:
        """Find a user's membership in one workspace."""


class AuthorizationUnitOfWork(Protocol):
    memberships: WorkspaceMembershipReader

    async def __aenter__(
        self,
    ) -> "AuthorizationUnitOfWork":
        """Open a read transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""
