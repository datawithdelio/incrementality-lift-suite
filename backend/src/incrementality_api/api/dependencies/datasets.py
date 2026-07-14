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


def get_upload_dataset_service() -> UploadDataset:
    """Construct the production dataset-upload use case."""

    raise RuntimeError("Dataset upload service is not configured.")
