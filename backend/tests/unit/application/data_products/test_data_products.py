from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from incrementality_api.application.data_products.explorer import (
    DatasetExplorer,
    DatasetExplorerQuery,
    DatasetFilter,
    MalformedDatasetError,
)
from incrementality_api.application.data_products.quality import (
    DataQualityAssessor,
    DataQualityInput,
)
from incrementality_api.application.data_products.report_jobs import ProcessNextReportJob, ReportJob
from incrementality_api.application.data_products.reports import (
    CsvReportRenderer,
    PdfReportRenderer,
    ReportModel,
)
from incrementality_api.application.data_products.services import (
    DatasetProductQuery,
    ProductionDataProducts,
)
from incrementality_api.application.datasets.errors import DatasetUnavailableError
from incrementality_api.application.datasets.ports import DatasetObjectWriteResult


def clean_rows(size: int = 40) -> tuple[dict[str, str], ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        {
            "date": (start + timedelta(days=index)).date().isoformat(),
            "market": f"market-{index % 8}",
            "treated": "yes" if index % 2 else "no",
            "revenue": str(100 + index * 2),
            "propensity": "0.5",
            "latitude": str(30 + index % 8),
            "longitude": str(-100 + index % 8),
            "search_spend": str(20 + index),
        }
        for index in range(size)
    )


def test_explorer_paginates_filters_sorts_and_profiles_without_returning_all_rows() -> None:
    result = DatasetExplorer().execute(
        clean_rows(250),
        DatasetExplorerQuery(
            page=2,
            page_size=25,
            sort_column="revenue",
            descending=True,
            filters=(DatasetFilter("treated", "equals", "yes"),),
            column_search="rev",
        ),
    )

    assert len(result.rows) == 25
    assert result.total_rows == 125
    assert result.total_pages == 5
    assert [column.name for column in result.columns] == ["revenue"]
    assert result.columns[0].inferred_type == "integer"
    assert result.columns[0].unique_count == 125
    assert result.date_range is not None


def test_explorer_rejects_malformed_rows_and_caps_page_size() -> None:
    with pytest.raises(MalformedDatasetError):
        DatasetExplorer().execute(({"a": "1"}, {"b": "2"}), DatasetExplorerQuery())

    with pytest.raises(ValueError, match="page size"):
        DatasetExplorerQuery(page_size=1001)


def test_quality_assessment_keeps_structured_findings_for_clean_weak_and_invalid_data() -> None:
    assessor = DataQualityAssessor()
    clean = assessor.assess(
        DataQualityInput(clean_rows(), estimator_type="difference_in_differences")
    )
    weak_rows = (*clean_rows(12), clean_rows(12)[0])
    weak = assessor.assess(DataQualityInput(weak_rows, estimator_type="difference_in_differences"))
    invalid_rows = tuple({**row, "revenue": ""} for row in clean_rows(10))
    invalid = assessor.assess(
        DataQualityInput(invalid_rows, estimator_type="difference_in_differences")
    )

    assert clean.ready is True
    assert clean.score >= 90
    assert any(item.rule_id == "duplicate_rows" for item in weak.findings)
    assert weak.score < clean.score
    assert invalid.ready is False
    blocker = next(item for item in invalid.findings if item.severity == "blocking")
    assert blocker.evidence
    assert blocker.recommendation


@pytest.mark.parametrize(
    ("estimator", "expected_rule"),
    [
        ("off_policy_evaluation", "propensity_overlap"),
        ("geo_holdout", "geo_coverage"),
        ("marketing_mix_model", "mmm_continuity"),
    ],
)
def test_quality_reports_method_specific_readiness(estimator: str, expected_rule: str) -> None:
    result = DataQualityAssessor().assess(DataQualityInput(clean_rows(8), estimator_type=estimator))
    assert any(item.rule_id == expected_rule for item in result.findings)


def report_model(*, causal_claim_allowed: bool = False) -> ReportModel:
    return ReportModel(
        title="Paid Search Incrementality",
        generated_at=datetime(2026, 7, 14, tzinfo=UTC),
        analysis_run_id="run-1",
        estimator="difference_in_differences",
        estimator_version="did-v2",
        dataset_id="dataset-1",
        dataset_checksum="abc123",
        mapping_version=3,
        configuration={"intervention_time": "2026-01-01"},
        estimate=8.2,
        confidence_low=4.4,
        confidence_high=12.0,
        diagnostics={"causal_claim_allowed": causal_claim_allowed},
        warnings=("Parallel trends are uncertain.",),
        business_impact={"incremental_revenue": 98400},
        quality_summary={"score": 82, "ready": True},
        limitations=("Observational design",),
    )


def test_report_renderers_are_reproducible_and_do_not_overstate_causality() -> None:
    model = report_model(causal_claim_allowed=False)
    csv_bytes = CsvReportRenderer().render(model)
    pdf_bytes = PdfReportRenderer().render(model)

    assert csv_bytes == CsvReportRenderer().render(model)
    assert b"directional association" in csv_bytes
    assert pdf_bytes.startswith(b"%PDF")
    assert b"causal increase" not in pdf_bytes


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 14, tzinfo=UTC)


class FakeReportRepository:
    def __init__(self, job: ReportJob) -> None:
        self.job, self.succeeded, self.failed = job, False, False
        self.succeeded_artifact: tuple[str, int | None, str | None] | None = None

    async def claim_next(self, now: datetime) -> ReportJob | None:
        return self.job

    async def succeed(
        self,
        job_id: object,
        storage_key: str,
        now: datetime,
        *,
        byte_size: int | None = None,
        checksum_sha256: str | None = None,
    ) -> ReportJob:
        del job_id, now

        self.succeeded = True
        self.succeeded_artifact = (
            storage_key,
            byte_size,
            checksum_sha256,
        )
        return self.job

    async def fail(self, job_id: object, error: str, now: datetime) -> ReportJob:
        self.failed = True
        return self.job


class FakeReportStorage:
    def __init__(self, fail: bool = False) -> None:
        self.fail, self.payload = fail, b""

    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: object,
    ) -> DatasetObjectWriteResult:
        del storage_key, media_type

        if self.fail:
            raise OSError("temporary storage outage")

        self.payload = b"".join(
            [
                item
                async for item in chunks  # type: ignore[attr-defined]
            ]
        )

        return DatasetObjectWriteResult(
            byte_size=len(self.payload),
            checksum_sha256=sha256(self.payload).hexdigest(),
        )


def queued_report() -> ReportJob:
    model = report_model()
    snapshot = {
        "title": model.title,
        "generated_at": model.generated_at,
        "analysis_run_id": model.analysis_run_id,
        "estimator": model.estimator,
        "estimator_version": model.estimator_version,
        "dataset_id": model.dataset_id,
        "dataset_checksum": model.dataset_checksum,
        "mapping_version": model.mapping_version,
        "configuration": dict(model.configuration),
        "estimate": model.estimate,
        "confidence_low": model.confidence_low,
        "confidence_high": model.confidence_high,
        "diagnostics": dict(model.diagnostics),
        "warnings": model.warnings,
        "business_impact": dict(model.business_impact),
        "quality_summary": dict(model.quality_summary),
        "limitations": model.limitations,
    }
    return ReportJob(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        1,
        "pdf",
        "running",
        1,
        3,
        snapshot,
        None,
        None,
        model.generated_at,
    )


async def test_report_job_generates_durable_output_and_retries_safe_failure() -> None:
    repository = FakeReportRepository(queued_report())
    storage = FakeReportStorage()
    await ProcessNextReportJob(repository=repository, storage=storage, clock=FakeClock()).execute()  # type: ignore[arg-type]
    assert repository.succeeded is True
    assert storage.payload.startswith(b"%PDF")

    expected_key = (
        f"reports/{repository.job.workspace_id}/"
        f"{repository.job.analysis_run_id}/"
        f"v{repository.job.version}.pdf"
    )

    assert repository.succeeded_artifact == (
        expected_key,
        len(storage.payload),
        sha256(storage.payload).hexdigest(),
    )

    failed_repository = FakeReportRepository(queued_report())
    await ProcessNextReportJob(
        repository=failed_repository, storage=FakeReportStorage(fail=True), clock=FakeClock()
    ).execute()  # type: ignore[arg-type]
    assert failed_repository.failed is True


class MissingDatasetReader:
    async def get_by_scope_read(self, **kwargs: object) -> None:
        return None


class UnusedMappingReader:
    pass


class CrossTenantUnitOfWork:
    datasets = MissingDatasetReader()
    semantic_mappings = UnusedMappingReader()

    async def __aenter__(self) -> "CrossTenantUnitOfWork":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


async def test_explorer_hides_cross_tenant_dataset() -> None:
    service = ProductionDataProducts(
        unit_of_work=CrossTenantUnitOfWork(), object_storage=object(), quality_writer=object()
    )  # type: ignore[arg-type]
    with pytest.raises(DatasetUnavailableError):
        await service.preview(
            DatasetProductQuery(uuid4(), uuid4(), uuid4()), DatasetExplorerQuery()
        )
