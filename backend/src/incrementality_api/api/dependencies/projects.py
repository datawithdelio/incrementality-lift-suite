from incrementality_api.application.projects.create_project import (
    CreateProject,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.projects import (
    SqlAlchemyProjectUnitOfWork,
)


def get_create_project_service() -> CreateProject:
    """Construct the production project-creation use case."""

    return CreateProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=get_session_factory(),
        )
    )
