from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incrementality_api.domain.projects.status import (
    ProjectStatus,
)


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )
    slug: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    name: str
    slug: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
    archived_at: datetime | None
