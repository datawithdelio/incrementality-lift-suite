from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.errors import (
    DatasetProjectUnavailableError,
    DatasetTooLargeError,
)
from incrementality_api.application.datasets.register_dataset import (
    RegisterDataset,
    RegisterDatasetCommand,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)
from incrementality_api.domain.projects.entities import Project

VALID_CHECKSUM = "a" * 64


class FakeDatasetRepository:
    def __init__(self) -> None:
        self.added_datasets: list[Dataset] = []

    async def add(
        self,
        dataset: Dataset,
    ) -> None:
        self.added_datasets.append(dataset)


class FakeDatasetProjectReader:
    def __init__(
        self,
        project: Project | None,
    ) -> None:
        self._project = project
        self.requested_project_id: UUID | None = None

    async def get_by_id(
        self,
        project_id: UUID,
    ) -> Project | None:
        self.requested_project_id = project_id
        return self._project


class FakeDatasetUnitOfWork:
    def __init__(
        self,
        project: Project | None,
    ) -> None:
        self.datasets = FakeDatasetRepository()
        self.projects = FakeDatasetProjectReader(project)
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeDatasetUnitOfWork":
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


class StubStorageKeyBuilder:
    def __init__(self) -> None:
        self.received_workspace_id: UUID | None = None
        self.received_project_id: UUID | None = None
        self.received_filename: str | None = None
        self.received_checksum: str | None = None

    def build(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        source_filename: str,
        checksum_sha256: str,
    ) -> str:
        self.received_workspace_id = workspace_id
        self.received_project_id = project_id
        self.received_filename = source_filename
        self.received_checksum = checksum_sha256

        return f"workspaces/{workspace_id}/projects/{project_id}/datasets/{checksum_sha256}.csv"


def build_project(
    *,
    workspace_id: UUID,
    archived: bool = False,
) -> Project:
    project = Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name="Incrementality Project",
        slug=f"project-{uuid4()}",
    )

    if archived:
        return project.archive(
            archived_at=datetime(
                2026,
                7,
                14,
                12,
                0,
                tzinfo=UTC,
            )
        )

    return project


def build_command(
    *,
    workspace_id: UUID,
    project_id: UUID,
    byte_size: int = 1024,
    source_filename: str = "campaign-results.csv",
) -> RegisterDatasetCommand:
    return RegisterDatasetCommand(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=uuid4(),
        source_filename=source_filename,
        media_type="TEXT/CSV",
        byte_size=byte_size,
        checksum_sha256=VALID_CHECKSUM,
    )


@pytest.mark.asyncio
async def test_registers_dataset_for_active_workspace_project() -> None:
    workspace_id = uuid4()
    project = build_project(
        workspace_id=workspace_id,
    )

    unit_of_work = FakeDatasetUnitOfWork(project)
    storage_key_builder = StubStorageKeyBuilder()

    service = RegisterDataset(
        unit_of_work=unit_of_work,
        storage_key_builder=storage_key_builder,
        maximum_upload_bytes=10_000,
    )

    command = build_command(
        workspace_id=workspace_id,
        project_id=project.id,
    )

    result = await service.execute(command)

    assert result.workspace_id == workspace_id
    assert result.project_id == project.id
    assert result.created_by_user_id == (command.created_by_user_id)
    assert result.media_type == "text/csv"
    assert result.status is DatasetStatus.PENDING_UPLOAD

    assert unit_of_work.projects.requested_project_id == (project.id)
    assert unit_of_work.datasets.added_datasets == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0

    assert storage_key_builder.received_workspace_id == (workspace_id)
    assert storage_key_builder.received_project_id == project.id


@pytest.mark.asyncio
async def test_rejects_dataset_exceeding_configured_limit() -> None:
    workspace_id = uuid4()
    project = build_project(
        workspace_id=workspace_id,
    )

    unit_of_work = FakeDatasetUnitOfWork(project)

    service = RegisterDataset(
        unit_of_work=unit_of_work,
        storage_key_builder=StubStorageKeyBuilder(),
        maximum_upload_bytes=1024,
    )

    with pytest.raises(
        DatasetTooLargeError,
        match="maximum upload size",
    ):
        await service.execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project.id,
                byte_size=1025,
            )
        )

    assert unit_of_work.projects.requested_project_id is None
    assert unit_of_work.datasets.added_datasets == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project",
    [
        None,
        build_project(
            workspace_id=uuid4(),
        ),
    ],
)
async def test_rejects_missing_or_cross_workspace_project(
    project: Project | None,
) -> None:
    requested_workspace_id = uuid4()
    requested_project_id = project.id if project is not None else uuid4()

    unit_of_work = FakeDatasetUnitOfWork(project)

    service = RegisterDataset(
        unit_of_work=unit_of_work,
        storage_key_builder=StubStorageKeyBuilder(),
        maximum_upload_bytes=10_000,
    )

    with pytest.raises(
        DatasetProjectUnavailableError,
        match="Dataset project is unavailable",
    ):
        await service.execute(
            build_command(
                workspace_id=requested_workspace_id,
                project_id=requested_project_id,
            )
        )

    assert unit_of_work.datasets.added_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_rejects_archived_project() -> None:
    workspace_id = uuid4()
    project = build_project(
        workspace_id=workspace_id,
        archived=True,
    )

    unit_of_work = FakeDatasetUnitOfWork(project)

    service = RegisterDataset(
        unit_of_work=unit_of_work,
        storage_key_builder=StubStorageKeyBuilder(),
        maximum_upload_bytes=10_000,
    )

    with pytest.raises(
        DatasetProjectUnavailableError,
        match="Dataset project is unavailable",
    ):
        await service.execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project.id,
            )
        )

    assert unit_of_work.datasets.added_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_invalid_dataset_metadata_is_not_persisted() -> None:
    workspace_id = uuid4()
    project = build_project(
        workspace_id=workspace_id,
    )

    unit_of_work = FakeDatasetUnitOfWork(project)

    service = RegisterDataset(
        unit_of_work=unit_of_work,
        storage_key_builder=StubStorageKeyBuilder(),
        maximum_upload_bytes=10_000,
    )

    with pytest.raises(
        InvalidDatasetError,
        match="Dataset filename",
    ):
        await service.execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project.id,
                source_filename="../unsafe.csv",
            )
        )

    assert unit_of_work.datasets.added_datasets == []
    assert unit_of_work.commit_count == 0
