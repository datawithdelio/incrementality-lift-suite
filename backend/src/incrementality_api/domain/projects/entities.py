from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.domain.projects.validation import (
    normalize_project_description,
    normalize_project_name,
    normalize_project_slug,
)


@dataclass(frozen=True, slots=True)
class Project:
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    name: str
    slug: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
    archived_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID,
        name: str,
        slug: str,
        description: str | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            name=normalize_project_name(name),
            slug=normalize_project_slug(slug),
            description=normalize_project_description(description),
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(UTC),
            archived_at=None,
        )

    def archive(
        self,
        *,
        archived_at: datetime,
    ) -> Self:
        if self.status is ProjectStatus.ARCHIVED:
            return self

        return replace(
            self,
            status=ProjectStatus.ARCHIVED,
            archived_at=archived_at,
        )

    def update_details(
        self,
        *,
        name: str,
        description: str | None,
    ) -> Self:
        return replace(
            self,
            name=normalize_project_name(name),
            description=normalize_project_description(description),
        )
