from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
)
from incrementality_api.application.datasets.ports import (
    DatasetColumnRepository,
    DatasetProjectReader,
    DatasetRepository,
    DatasetSemanticMappingRepository,
)
from incrementality_api.application.jobs.ports import (
    DatasetValidationJobRepository,
)
from incrementality_api.infrastructure.database.repositories.dataset_columns import (
    SqlAlchemyDatasetColumnRepository,
)
from incrementality_api.infrastructure.database.repositories.dataset_semantic_mappings import (
    SqlAlchemyDatasetSemanticMappingRepository,
)
from incrementality_api.infrastructure.database.repositories.datasets import (
    SqlAlchemyDatasetProjectReader,
    SqlAlchemyDatasetRepository,
)
from incrementality_api.infrastructure.database.repositories.jobs import (
    SqlAlchemyDatasetValidationJobRepository,
)


class SqlAlchemyDatasetUnitOfWork:
    """Own one SQLAlchemy dataset transaction."""

    datasets: DatasetRepository
    columns: DatasetColumnRepository
    semantic_mappings: DatasetSemanticMappingRepository
    projects: DatasetProjectReader
    validation_jobs: DatasetValidationJobRepository

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyDatasetUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.datasets = SqlAlchemyDatasetRepository(
            session=session,
        )
        self.columns = SqlAlchemyDatasetColumnRepository(
            session=session,
        )
        self.semantic_mappings = SqlAlchemyDatasetSemanticMappingRepository(
            session=session,
        )
        self.projects = SqlAlchemyDatasetProjectReader(
            session=session,
        )
        self.validation_jobs = SqlAlchemyDatasetValidationJobRepository(
            session=session,
        )

        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        session = self._require_session()

        try:
            if exception_type is not None:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        session = self._require_session()

        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()

            raise DatasetPersistenceConflictError(
                "Dataset metadata conflicts with an existing record."
            ) from error

    async def rollback(self) -> None:
        session = self._require_session()
        await session.rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("The dataset Unit of Work must be entered before use.")

        return self._session
