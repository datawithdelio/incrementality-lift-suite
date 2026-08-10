from datetime import UTC, datetime
from typing import cast

from incrementality_api.application.analysis_execution.input_loading import (
    AnalysisPeriodRowFilter,
    CsvAnalysisRowLoader,
)
from incrementality_api.application.data_products.mmm_design_summary import (
    MarketingMixDesignSummaryBuilder,
    MarketingMixDesignSummaryPlanner,
)
from incrementality_api.application.data_products.services import (
    DatasetProductUnitOfWork,
    ProductionDataProducts,
)
from incrementality_api.core.config import get_settings
from incrementality_api.infrastructure.database.repositories.data_products import (
    SqlAlchemyDatasetVersionReader,
    SqlAlchemyQualityAssessmentWriter,
    SqlAlchemyReportRepository,
)
from incrementality_api.infrastructure.database.session import get_session_factory
from incrementality_api.infrastructure.database.unit_of_work.datasets import (
    SqlAlchemyDatasetUnitOfWork,
)
from incrementality_api.infrastructure.analysis_execution.selection import (
    AnalysisSelectionRowExecutor,
)
from incrementality_api.infrastructure.storage.s3_clients import create_s3_compatible_client
from incrementality_api.infrastructure.storage.s3_dataset_objects import S3DatasetObjectStorage


class SystemDataProductClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def get_data_product_storage() -> S3DatasetObjectStorage:
    settings = get_settings()
    client = create_s3_compatible_client(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )
    return S3DatasetObjectStorage(
        client=client,
        bucket_name=settings.s3_bucket,
        spool_max_memory_bytes=settings.dataset_validation_spool_max_memory_bytes,
    )


def get_data_products_service() -> ProductionDataProducts:
    sessions = get_session_factory()
    return ProductionDataProducts(
        unit_of_work=cast(
            DatasetProductUnitOfWork,
            SqlAlchemyDatasetUnitOfWork(sessions),
        ),
        object_storage=get_data_product_storage(),
        quality_writer=SqlAlchemyQualityAssessmentWriter(sessions, SystemDataProductClock()),
        row_loader=CsvAnalysisRowLoader(),
        mmm_design_summary_planner=MarketingMixDesignSummaryPlanner(
            period_filter=AnalysisPeriodRowFilter(),
            selection_executor=AnalysisSelectionRowExecutor(),
            summary_builder=MarketingMixDesignSummaryBuilder(),
        ),
    )


def get_report_repository() -> SqlAlchemyReportRepository:
    return SqlAlchemyReportRepository(get_session_factory())


def get_dataset_version_reader() -> SqlAlchemyDatasetVersionReader:
    return SqlAlchemyDatasetVersionReader(get_session_factory())
