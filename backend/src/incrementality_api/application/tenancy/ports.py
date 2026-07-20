from types import TracebackType
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from incrementality_api.application.tenancy.list_user_workspaces import (
        AccessibleWorkspace,
    )
    from incrementality_api.application.tenancy.list_workspace_members import (
        WorkspaceMember,
    )

from incrementality_api.domain.authentication.entities import (
    PasswordCredential,
)
from incrementality_api.domain.tenancy.entities import (
    Organization,
    User,
    Workspace,
    WorkspaceMembership,
)


class OrganizationRepository(Protocol):
    async def add(self, organization: Organization) -> None:
        """Persist an organization inside the transaction."""


class UserRepository(Protocol):
    async def add(self, user: User) -> None:
        """Persist a user inside the transaction."""


class CredentialRepository(Protocol):
    async def add(
        self,
        credential: PasswordCredential,
    ) -> None:
        """Persist a password credential inside the transaction."""


class WorkspaceRepository(Protocol):
    async def add(self, workspace: Workspace) -> None:
        """Persist a workspace inside the transaction."""


class MembershipRepository(Protocol):
    async def add(
        self,
        membership: WorkspaceMembership,
    ) -> None:
        """Persist a membership inside the transaction."""


class TenancyUnitOfWork(Protocol):
    organizations: OrganizationRepository
    users: UserRepository
    credentials: CredentialRepository
    workspaces: WorkspaceRepository
    memberships: MembershipRepository

    async def __aenter__(self) -> "TenancyUnitOfWork":
        """Begin a transaction scope."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close or roll back the transaction scope."""

    async def commit(self) -> None:
        """Commit the current transaction."""

    async def rollback(self) -> None:
        """Roll back the current transaction."""



class WorkspaceAccessReader(Protocol):
    async def list_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list["AccessibleWorkspace"]:
        """List workspaces accessible to one user."""

class WorkspaceMemberReader(Protocol):
    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
    ) -> list["WorkspaceMember"]:
        """List safe member details for one workspace."""
