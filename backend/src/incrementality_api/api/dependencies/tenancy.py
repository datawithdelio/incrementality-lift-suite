from collections.abc import AsyncIterator

from incrementality_api.application.tenancy.create_workspace import (
    CreateWorkspace,
)
from incrementality_api.application.tenancy.list_user_workspaces import (
    ListUserWorkspaces,
)
from incrementality_api.application.tenancy.list_workspace_members import (
    ListWorkspaceMembers,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
)
from incrementality_api.infrastructure.database.repositories.tenancy import (
    SqlAlchemyWorkspaceAccessReader,
    SqlAlchemyWorkspaceMemberReader,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.tenancy import (
    SqlAlchemyTenancyUnitOfWork,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)


def get_create_workspace_service() -> CreateWorkspace:
    """Build the authenticated workspace-creation use case."""

    return CreateWorkspace(
        unit_of_work=SqlAlchemyTenancyUnitOfWork(
            session_factory=get_session_factory(),
        ),
    )

def get_provision_tenant() -> ProvisionTenant:
    """Build one tenant-provisioning use case per request."""

    return ProvisionTenant(
        unit_of_work=SqlAlchemyTenancyUnitOfWork(
            session_factory=get_session_factory(),
        ),
        password_hasher=Argon2PasswordHasher(),
    )



async def get_list_user_workspaces_service() -> AsyncIterator[ListUserWorkspaces]:
    """Build a workspace-listing service with a request-scoped session."""

    session_factory = get_session_factory()

    async with session_factory() as session:
        yield ListUserWorkspaces(
            reader=SqlAlchemyWorkspaceAccessReader(
                session=session,
            ),
        )


async def get_list_workspace_members_service() -> AsyncIterator[ListWorkspaceMembers]:
    """Build a workspace-member reader with a request-scoped session."""

    session_factory = get_session_factory()

    async with session_factory() as session:
        yield ListWorkspaceMembers(
            reader=SqlAlchemyWorkspaceMemberReader(
                session=session,
            ),
        )
