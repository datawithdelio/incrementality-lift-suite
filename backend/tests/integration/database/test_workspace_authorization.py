from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizeWorkspaceAction,
)
from incrementality_api.application.authorization.errors import (
    WorkspaceAccessDeniedError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.authorization.policy import (
    WorkspaceAccessPolicy,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceMembershipModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.unit_of_work.authorization import (
    SqlAlchemyAuthorizationUnitOfWork,
)

FIXED_NOW = datetime(
    2026,
    7,
    13,
    22,
    0,
    tzinfo=UTC,
)


async def seed_workspace_membership(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    role: WorkspaceRole,
) -> tuple[UUID, UUID, UUID]:
    organization_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add(
            OrganizationModel(
                id=organization_id,
                name="Acme Media",
                slug=f"acme-{organization_id}",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

        session.add(
            UserModel(
                id=user_id,
                email=f"{user_id}@example.com",
                display_name="Workspace User",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Marketing Science",
                slug=f"workspace-{workspace_id}",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

        session.add(
            WorkspaceMembershipModel(
                id=membership_id,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role.value,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

    return workspace_id, user_id, membership_id


@pytest.mark.asyncio
async def test_authorizes_member_using_postgres_role(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, user_id, membership_id = await seed_workspace_membership(
        tenancy_session_factory,
        role=WorkspaceRole.ANALYST,
    )

    service = AuthorizeWorkspaceAction(
        unit_of_work=SqlAlchemyAuthorizationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        policy=WorkspaceAccessPolicy(),
    )

    result = await service.execute(
        workspace_id=workspace_id,
        user_id=user_id,
        permission=WorkspacePermission.RUN_ANALYSES,
    )

    assert result.workspace_id == workspace_id
    assert result.user_id == user_id
    assert result.membership_id == membership_id
    assert result.role is WorkspaceRole.ANALYST


@pytest.mark.asyncio
async def test_rejects_insufficient_postgres_role(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, user_id, _ = await seed_workspace_membership(
        tenancy_session_factory,
        role=WorkspaceRole.VIEWER,
    )

    service = AuthorizeWorkspaceAction(
        unit_of_work=SqlAlchemyAuthorizationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        policy=WorkspaceAccessPolicy(),
    )

    with pytest.raises(
        WorkspaceAccessDeniedError,
        match="Workspace access denied",
    ):
        await service.execute(
            workspace_id=workspace_id,
            user_id=user_id,
            permission=WorkspacePermission.RUN_ANALYSES,
        )


@pytest.mark.asyncio
async def test_rejects_user_without_postgres_membership(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, _, _ = await seed_workspace_membership(
        tenancy_session_factory,
        role=WorkspaceRole.OWNER,
    )

    service = AuthorizeWorkspaceAction(
        unit_of_work=SqlAlchemyAuthorizationUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        policy=WorkspaceAccessPolicy(),
    )

    with pytest.raises(
        WorkspaceAccessDeniedError,
        match="Workspace access denied",
    ):
        await service.execute(
            workspace_id=workspace_id,
            user_id=uuid4(),
            permission=WorkspacePermission.VIEW_WORKSPACE,
        )
