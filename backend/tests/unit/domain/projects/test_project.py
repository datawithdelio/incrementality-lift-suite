from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.domain.projects.entities import Project
from incrementality_api.domain.projects.errors import (
    InvalidProjectError,
)
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)

ARCHIVED_AT = datetime(
    2026,
    7,
    14,
    12,
    0,
    tzinfo=UTC,
)


def create_project(
    *,
    workspace_id: UUID | None = None,
    created_by_user_id: UUID | None = None,
    name: str = "Incrementality Measurement",
    slug: str = "incrementality-measurement",
    description: str | None = ("Measure campaign incrementality and causal lift."),
) -> Project:
    return Project.create(
        workspace_id=workspace_id or uuid4(),
        created_by_user_id=created_by_user_id or uuid4(),
        name=name,
        slug=slug,
        description=description,
    )


def test_creates_active_project_inside_workspace() -> None:
    workspace_id = uuid4()
    created_by_user_id = uuid4()

    project = create_project(
        workspace_id=workspace_id,
        created_by_user_id=created_by_user_id,
    )

    assert isinstance(project.id, UUID)
    assert project.workspace_id == workspace_id
    assert project.created_by_user_id == created_by_user_id
    assert project.name == "Incrementality Measurement"
    assert project.slug == "incrementality-measurement"
    assert project.description == ("Measure campaign incrementality and causal lift.")
    assert project.status is ProjectStatus.ACTIVE
    assert project.archived_at is None
    assert project.created_at.utcoffset() == timedelta(0)


def test_project_name_is_trimmed() -> None:
    project = create_project(
        name="  Incrementality Measurement  ",
    )

    assert project.name == "Incrementality Measurement"


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_rejects_blank_project_name(name: str) -> None:
    with pytest.raises(
        InvalidProjectError,
        match="Project name",
    ):
        create_project(name=name)


def test_rejects_project_name_longer_than_200_characters() -> None:
    with pytest.raises(
        InvalidProjectError,
        match="Project name",
    ):
        create_project(name="x" * 201)


def test_project_slug_is_trimmed_and_lowercased() -> None:
    project = create_project(
        slug="  Incrementality-Measurement  ",
    )

    assert project.slug == "incrementality-measurement"


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "marketing lift",
        "marketing_lift",
        "-marketing-lift",
        "marketing-lift-",
    ],
)
def test_rejects_invalid_project_slug(slug: str) -> None:
    with pytest.raises(
        InvalidProjectError,
        match="Project slug",
    ):
        create_project(slug=slug)


def test_rejects_project_slug_longer_than_100_characters() -> None:
    with pytest.raises(
        InvalidProjectError,
        match="Project slug",
    ):
        create_project(slug="x" * 101)


def test_blank_description_becomes_none() -> None:
    project = create_project(
        description="   ",
    )

    assert project.description is None


def test_project_description_is_trimmed() -> None:
    project = create_project(
        description="  Geo experiment for paid search.  ",
    )

    assert project.description == ("Geo experiment for paid search.")


def test_rejects_description_longer_than_2000_characters() -> None:
    with pytest.raises(
        InvalidProjectError,
        match="Project description",
    ):
        create_project(description="x" * 2001)


def test_archives_project_without_deleting_identity() -> None:
    project = create_project()

    archived = project.archive(
        archived_at=ARCHIVED_AT,
    )

    assert archived.id == project.id
    assert archived.workspace_id == project.workspace_id
    assert archived.created_by_user_id == (project.created_by_user_id)
    assert archived.created_at == project.created_at
    assert archived.status is ProjectStatus.ARCHIVED
    assert archived.archived_at == ARCHIVED_AT

    assert project.status is ProjectStatus.ACTIVE
    assert project.archived_at is None


def test_archiving_is_idempotent_and_preserves_original_time() -> None:
    project = create_project()

    first_archive = project.archive(
        archived_at=ARCHIVED_AT,
    )

    second_archive = first_archive.archive(
        archived_at=ARCHIVED_AT + timedelta(days=1),
    )

    assert second_archive == first_archive
    assert second_archive.archived_at == ARCHIVED_AT


def test_updates_project_details_without_changing_identity() -> None:
    project = create_project(
        name="Original Study",
        description="Original description.",
    )

    updated = project.update_details(
        name="  Summer Campaign Lift  ",
        description="  Updated measurement objective.  ",
    )

    assert updated.id == project.id
    assert updated.workspace_id == project.workspace_id
    assert updated.created_by_user_id == project.created_by_user_id
    assert updated.slug == project.slug
    assert updated.created_at == project.created_at
    assert updated.name == "Summer Campaign Lift"
    assert updated.description == "Updated measurement objective."
    assert project.name == "Original Study"
