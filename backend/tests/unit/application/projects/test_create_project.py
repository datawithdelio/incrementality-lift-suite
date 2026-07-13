from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.projects.create_project import (
    CreateProject,
    CreateProjectCommand,
)
from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.domain.projects.entities import Project
from incrementality_api.domain.projects.errors import (
    InvalidProjectError,
)
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)


class FakeProjectRepository:
    def __init__(
        self,
        existing_project: Project | None = None,
    ) -> None:
        self._existing_project = existing_project

        self.requested_workspace_id: UUID | None = None
        self.requested_slug: str | None = None
        self.added_projects: list[Project] = []

    async def get_by_workspace_and_slug(
        self,
        *,
        workspace_id: UUID,
        slug: str,
    ) -> Project | None:
        self.requested_workspace_id = workspace_id
        self.requested_slug = slug

        return self._existing_project

    async def add(
        self,
        project: Project,
    ) -> None:
        self.added_projects.append(project)


class FakeProjectUnitOfWork:
    def __init__(
        self,
        existing_project: Project | None = None,
    ) -> None:
        self.projects = FakeProjectRepository(
            existing_project,
        )
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeProjectUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        if exception_type is not None:
            self.rollback_count += 1

    async def commit(self) -> None:
        self.commit_count += 1


def build_existing_project(
    *,
    workspace_id: UUID,
    slug: str,
) -> Project:
    return Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name="Existing Project",
        slug=slug,
    )


@pytest.mark.asyncio
async def test_creates_and_persists_project() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    unit_of_work = FakeProjectUnitOfWork()

    service = CreateProject(
        unit_of_work=unit_of_work,
    )

    result = await service.execute(
        CreateProjectCommand(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            name="  Paid Search Incrementality  ",
            slug="  Paid-Search-Lift  ",
            description="  Geo holdout study.  ",
        )
    )

    assert result.workspace_id == workspace_id
    assert result.created_by_user_id == user_id
    assert result.name == "Paid Search Incrementality"
    assert result.slug == "paid-search-lift"
    assert result.description == "Geo holdout study."
    assert result.status is ProjectStatus.ACTIVE

    assert unit_of_work.projects.requested_workspace_id == (workspace_id)
    assert unit_of_work.projects.requested_slug == ("paid-search-lift")
    assert unit_of_work.projects.added_projects == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_rejects_duplicate_slug_in_same_workspace() -> None:
    workspace_id = uuid4()

    existing_project = build_existing_project(
        workspace_id=workspace_id,
        slug="paid-search-lift",
    )

    unit_of_work = FakeProjectUnitOfWork(
        existing_project,
    )

    service = CreateProject(
        unit_of_work=unit_of_work,
    )

    with pytest.raises(
        DuplicateProjectSlugError,
        match="already exists",
    ):
        await service.execute(
            CreateProjectCommand(
                workspace_id=workspace_id,
                created_by_user_id=uuid4(),
                name="Another Project",
                slug="  PAID-SEARCH-LIFT  ",
            )
        )

    assert unit_of_work.projects.requested_slug == ("paid-search-lift")
    assert unit_of_work.projects.added_projects == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_invalid_project_is_not_persisted() -> None:
    unit_of_work = FakeProjectUnitOfWork()

    service = CreateProject(
        unit_of_work=unit_of_work,
    )

    with pytest.raises(
        InvalidProjectError,
        match="Project name",
    ):
        await service.execute(
            CreateProjectCommand(
                workspace_id=uuid4(),
                created_by_user_id=uuid4(),
                name="   ",
                slug="valid-slug",
            )
        )

    assert unit_of_work.projects.added_projects == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_slug_lookup_is_scoped_to_requested_workspace() -> None:
    requested_workspace_id = uuid4()

    unit_of_work = FakeProjectUnitOfWork()

    service = CreateProject(
        unit_of_work=unit_of_work,
    )

    result = await service.execute(
        CreateProjectCommand(
            workspace_id=requested_workspace_id,
            created_by_user_id=uuid4(),
            name="Incrementality Study",
            slug="shared-slug",
        )
    )

    assert result.workspace_id == requested_workspace_id
    assert unit_of_work.projects.requested_workspace_id == (requested_workspace_id)
    assert unit_of_work.projects.requested_slug == "shared-slug"
