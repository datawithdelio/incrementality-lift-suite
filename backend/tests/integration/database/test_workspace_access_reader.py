from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceMembershipModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.repositories.tenancy import (
    SqlAlchemyWorkspaceAccessReader,
)

NOW = datetime(
    2026,
    7,
    17,
    12,
    0,
    tzinfo=UTC,
)


@pytest.mark.asyncio
async def test_workspace_access_reader_returns_only_users_workspaces(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = uuid4()
    user_a_id = uuid4()
    user_b_id = uuid4()

    workspace_a1_id = uuid4()
    workspace_a2_id = uuid4()
    workspace_b_id = uuid4()

    async with tenancy_session_factory() as session, session.begin():
        session.add(
            OrganizationModel(
                id=organization_id,
                name="Acme Media",
                slug="acme-media",
                created_at=NOW,
                updated_at=NOW,
            )
        )

        session.add_all(
            [
                UserModel(
                    id=user_a_id,
                    email="user-a@example.com",
                    display_name="User A",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                UserModel(
                    id=user_b_id,
                    email="user-b@example.com",
                    display_name="User B",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )

        session.add_all(
            [
                WorkspaceModel(
                    id=workspace_a1_id,
                    organization_id=organization_id,
                    name="Analytics",
                    slug="analytics",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceModel(
                    id=workspace_a2_id,
                    organization_id=organization_id,
                    name="Marketing Science",
                    slug="marketing-science",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceModel(
                    id=workspace_b_id,
                    organization_id=organization_id,
                    name="Private Workspace",
                    slug="private-workspace",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )

        await session.flush()

        session.add_all(
            [
                WorkspaceMembershipModel(
                    id=uuid4(),
                    workspace_id=workspace_a1_id,
                    user_id=user_a_id,
                    role="owner",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceMembershipModel(
                    id=uuid4(),
                    workspace_id=workspace_a2_id,
                    user_id=user_a_id,
                    role="analyst",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceMembershipModel(
                    id=uuid4(),
                    workspace_id=workspace_b_id,
                    user_id=user_b_id,
                    role="owner",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )

    async with tenancy_session_factory() as session:
        reader = SqlAlchemyWorkspaceAccessReader(
            session=session,
        )

        result = await reader.list_for_user(
            user_id=user_a_id,
        )

    assert [
        (
            workspace.workspace_id,
            workspace.organization_id,
            workspace.name,
            workspace.slug,
            workspace.role,
        )
        for workspace in result
    ] == [
        (
            workspace_a1_id,
            organization_id,
            "Analytics",
            "analytics",
            "owner",
        ),
        (
            workspace_a2_id,
            organization_id,
            "Marketing Science",
            "marketing-science",
            "analyst",
        ),
    ]

    assert all(
        workspace.workspace_id != workspace_b_id
        for workspace in result
    )


@pytest.mark.asyncio
async def test_workspace_access_reader_returns_empty_list_without_memberships(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with tenancy_session_factory() as session:
        reader = SqlAlchemyWorkspaceAccessReader(
            session=session,
        )

        result = await reader.list_for_user(
            user_id=uuid4(),
        )

    assert result == []
