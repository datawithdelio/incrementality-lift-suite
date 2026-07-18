from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.projects.create_project import (
    CreateProject,
    CreateProjectCommand,
)
from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.application.projects.manage_projects import (
    GetWorkspaceProject,
    GetWorkspaceProjectOverview,
    ListWorkspaceProjects,
    UpdateWorkspaceProject,
)
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.unit_of_work.projects import (
    SqlAlchemyProjectUnitOfWork,
)

FIXED_NOW = datetime(
    2026,
    7,
    14,
    1,
    0,
    tzinfo=UTC,
)


async def seed_workspace(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    organization_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Project Organization",
                    slug=f"organization-{organization_id}",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Project Creator",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
            ]
        )

        await session.flush()

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Measurement Workspace",
                slug=f"workspace-{workspace_id}",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

    return workspace_id, user_id


def build_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> CreateProject:
    return CreateProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=session_factory,
        )
    )


@pytest.mark.asyncio
async def test_persists_and_reads_project_from_postgres(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, user_id = await seed_workspace(
        tenancy_session_factory,
    )

    created = await build_service(
        tenancy_session_factory,
    ).execute(
        CreateProjectCommand(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            name="Paid Search Incrementality",
            slug="paid-search-lift",
            description="Geo holdout measurement.",
        )
    )

    async with SqlAlchemyProjectUnitOfWork(
        session_factory=tenancy_session_factory,
    ) as unit_of_work:
        loaded = await unit_of_work.projects.get_by_workspace_and_slug(
            workspace_id=workspace_id,
            slug="paid-search-lift",
        )

    assert loaded == created


@pytest.mark.asyncio
async def test_lists_and_updates_projects_without_crossing_workspace_boundary(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, user_id = await seed_workspace(tenancy_session_factory)
    other_workspace_id, other_user_id = await seed_workspace(tenancy_session_factory)
    project = await build_service(tenancy_session_factory).execute(
        CreateProjectCommand(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            name="Workspace Project",
            slug="workspace-project",
        )
    )
    await build_service(tenancy_session_factory).execute(
        CreateProjectCommand(
            workspace_id=other_workspace_id,
            created_by_user_id=other_user_id,
            name="Private Project",
            slug="private-project",
        )
    )

    listed = await ListWorkspaceProjects(
        unit_of_work=SqlAlchemyProjectUnitOfWork(tenancy_session_factory),
    ).execute(workspace_id=workspace_id)
    updated = await UpdateWorkspaceProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(tenancy_session_factory),
    ).execute(
        workspace_id=workspace_id,
        project_id=project.id,
        name="Renamed Workspace Project",
        description="Updated safely.",
    )
    restored = await GetWorkspaceProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(tenancy_session_factory),
    ).execute(workspace_id=workspace_id, project_id=project.id)
    overview = await GetWorkspaceProjectOverview(
        unit_of_work=SqlAlchemyProjectUnitOfWork(tenancy_session_factory),
    ).execute(workspace_id=workspace_id, project_id=project.id)

    assert [item.id for item in listed] == [project.id]
    assert updated.name == "Renamed Workspace Project"
    assert updated.slug == "workspace-project"
    assert restored == updated
    assert overview.workflow.latest_dataset_id is None
    assert overview.workflow.latest_analysis_run_id is None
    assert overview.workflow.semantic_mapping_configured is False


@pytest.mark.asyncio
async def test_allows_same_slug_in_different_workspaces(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_workspace_id, first_user_id = await seed_workspace(
        tenancy_session_factory,
    )
    second_workspace_id, second_user_id = await seed_workspace(
        tenancy_session_factory,
    )

    first_project = await build_service(
        tenancy_session_factory,
    ).execute(
        CreateProjectCommand(
            workspace_id=first_workspace_id,
            created_by_user_id=first_user_id,
            name="First Workspace Project",
            slug="shared-project",
        )
    )

    second_project = await build_service(
        tenancy_session_factory,
    ).execute(
        CreateProjectCommand(
            workspace_id=second_workspace_id,
            created_by_user_id=second_user_id,
            name="Second Workspace Project",
            slug="shared-project",
        )
    )

    assert first_project.workspace_id == first_workspace_id
    assert second_project.workspace_id == second_workspace_id
    assert first_project.slug == second_project.slug


@pytest.mark.asyncio
async def test_rejects_duplicate_slug_in_same_workspace(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, user_id = await seed_workspace(
        tenancy_session_factory,
    )

    service = build_service(
        tenancy_session_factory,
    )

    await service.execute(
        CreateProjectCommand(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            name="Original Project",
            slug="duplicate-project",
        )
    )

    with pytest.raises(
        DuplicateProjectSlugError,
        match="already exists",
    ):
        await service.execute(
            CreateProjectCommand(
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="Duplicate Project",
                slug="DUPLICATE-PROJECT",
            )
        )

    async with tenancy_session_factory() as session:
        project_count = await session.scalar(
            select(func.count())
            .select_from(ProjectModel)
            .where(
                ProjectModel.workspace_id == workspace_id,
                ProjectModel.slug == "duplicate-project",
            )
        )

    assert project_count == 1
