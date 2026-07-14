from datetime import UTC, datetime

from incrementality_api.application.datasets.manage_semantic_mapping import (
    CreateDatasetSemanticMapping,
    GetDatasetSemanticMapping,
)
from incrementality_api.application.datasets.read_dataset import (
    GetDataset,
    ListDatasetColumns,
)
from incrementality_api.application.datasets.register_dataset import (
    RegisterDataset,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
)
from incrementality_api.core.config import get_settings
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.datasets import (
    SqlAlchemyDatasetUnitOfWork,
)
from incrementality_api.infrastructure.storage.dataset_keys import (
    DatasetObjectKeyBuilder,
)
from incrementality_api.infrastructure.storage.s3_clients import (
    create_s3_compatible_client,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)


class SystemDatasetClock:
    """Provide timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def get_register_dataset_service() -> RegisterDataset:
    """Construct the production dataset-registration use case."""

    settings = get_settings()

    return RegisterDataset(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=get_session_factory(),
        ),
        storage_key_builder=DatasetObjectKeyBuilder(),
        maximum_upload_bytes=(settings.dataset_max_upload_bytes),
    )


def get_read_dataset_service() -> GetDataset:
    """Construct the production dataset-read use case."""

    return GetDataset(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=get_session_factory(),
        ),
    )


def get_list_dataset_columns_service() -> ListDatasetColumns:
    """Construct the production column-list use case."""

    return ListDatasetColumns(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=get_session_factory(),
        ),
    )


def get_upload_dataset_service() -> UploadDataset:
    """Construct the production dataset-upload use case."""

    settings = get_settings()

    client = create_s3_compatible_client(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )

    object_storage = S3DatasetObjectStorage(
        client=client,
        bucket_name=settings.s3_bucket,
        spool_max_memory_bytes=(settings.dataset_upload_spool_max_memory_bytes),
    )

    return UploadDataset(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=get_session_factory(),
        ),
        object_storage=object_storage,
        clock=SystemDatasetClock(),
    )


def get_create_dataset_semantic_mapping_service() -> CreateDatasetSemanticMapping:
    """Construct semantic-mapping creation orchestration."""

    return CreateDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=get_session_factory(),
        ),
        clock=SystemDatasetClock(),
    )


def get_read_dataset_semantic_mapping_service() -> GetDatasetSemanticMapping:
    """Construct semantic-mapping read orchestration."""

    return GetDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=get_session_factory(),
        ),
    )
