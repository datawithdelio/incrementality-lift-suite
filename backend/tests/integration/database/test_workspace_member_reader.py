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
    SqlAlchemyWorkspaceMemberReader,
)

NOW = datetime(
    2026,
    7,
    19,
    12,
    0,
    tzinfo=UTC,
)


@pytest.mark.asyncio
async def test_workspace_member_reader_does_not_leak_members_across_workspaces(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = uuid4()

    workspace_a_id = uuid4()
    workspace_b_id = uuid4()

    owner_a_id = uuid4()
    analyst_a_id = uuid4()
    owner_b_id = uuid4()

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(
            OrganizationModel(
                id=organization_id,
                name="Measurement Company",
                slug="measurement-company",
                created_at=NOW,
                updated_at=NOW,
            )
        )

        session.add_all(
            [
                UserModel(
                    id=owner_a_id,
                    email="owner-a@example.com",
                    display_name="Owner A",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                UserModel(
                    id=analyst_a_id,
                    email="analyst-a@example.com",
                    display_name="Analyst A",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                UserModel(
                    id=owner_b_id,
                    email="owner-b@example.com",
                    display_name="Owner B",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )

        session.add_all(
            [
                WorkspaceModel(
                    id=workspace_a_id,
                    organization_id=organization_id,
                    name="Workspace A",
                    slug="workspace-a",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceModel(
                    id=workspace_b_id,
                    organization_id=organization_id,
                    name="Workspace B",
                    slug="workspace-b",
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
                    workspace_id=workspace_a_id,
                    user_id=owner_a_id,
                    role="owner",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceMembershipModel(
                    id=uuid4(),
                    workspace_id=workspace_a_id,
                    user_id=analyst_a_id,
                    role="analyst",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                WorkspaceMembershipModel(
                    id=uuid4(),
                    workspace_id=workspace_b_id,
                    user_id=owner_b_id,
                    role="owner",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )

    async with tenancy_session_factory() as session:
        reader = SqlAlchemyWorkspaceMemberReader(
            session=session,
        )

        members = await reader.list_for_workspace(
            workspace_id=workspace_a_id,
        )

    assert [
        (
            member.display_name,
            member.email,
            member.role,
            member.joined_at,
        )
        for member in members
    ] == [
        (
            "Analyst A",
            "analyst-a@example.com",
            "analyst",
            NOW,
        ),
        (
            "Owner A",
            "owner-a@example.com",
            "owner",
            NOW,
        ),
    ]

    assert all(
        member.email
        != "owner-b@example.com"
        for member in members
    )


@pytest.mark.asyncio
async def test_workspace_member_reader_returns_empty_for_unknown_workspace(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with tenancy_session_factory() as session:
        reader = SqlAlchemyWorkspaceMemberReader(
            session=session,
        )

        members = await reader.list_for_workspace(
            workspace_id=uuid4(),
        )

    assert members == []
