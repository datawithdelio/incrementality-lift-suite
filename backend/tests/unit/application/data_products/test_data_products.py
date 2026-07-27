from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from incrementality_api.application.data_products.explorer import (
    DatasetExplorer,
    DatasetExplorerQuery,
    DatasetFilter,
    ExplorerSemanticMapping,
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


def test_explorer_builds_mapped_visual_evidence_from_the_complete_filtered_dataset() -> None:
    rows = (
        {
            "date": "2026-01-01",
            "market": "Boston",
            "region": "East",
            "treated": "no",
            "post_period": "0",
            "revenue": "100",
        },
        {
            "date": "2026-01-01",
            "market": "New York",
            "region": "East",
            "treated": "yes",
            "post_period": "0",
            "revenue": "110",
        },
        {
            "date": "2026-02-01",
            "market": "Boston",
            "region": "",
            "treated": "no",
            "post_period": "1",
            "revenue": "105",
        },
        {
            "date": "2026-02-01",
            "market": "New York",
            "region": "East",
            "treated": "yes",
            "post_period": "1",
            "revenue": "145",
        },
        {
            "date": "2026-02-01",
            "market": "Chicago",
            "region": "West",
            "treated": "yes",
            "post_period": "1",
            "revenue": "150",
        },
    )

    result = DatasetExplorer().execute(
        rows,
        DatasetExplorerQuery(page=1, page_size=2),
        ExplorerSemanticMapping(
            time_column="date",
            unit_column="market",
            treatment_column="treated",
            outcome_column="revenue",
            treatment_value="yes",
            control_value="no",
        ),
    )

    assert len(result.rows) == 2
    assert result.visualizations.outcome_column == "revenue"
    assert result.visualizations.treatment_start_date == "2026-02-01"
    assert result.visualizations.trend[-1].treatment_value == pytest.approx(147.5)
    assert result.visualizations.trend[-1].control_value == pytest.approx(105)
    assert result.visualizations.trend[-1].treatment_observations == 2
    assert result.visualizations.distribution.median == 110
    assert result.visualizations.distribution.sample_size == 5
    region_missingness = next(
        item
        for item in result.visualizations.missingness
        if item.column == "region"
    )
    assert region_missingness.missing_count == 1
    assert result.visualizations.balance.treatment_label == "Treatment"
    assert result.visualizations.balance.control_label == "Control"
    assert result.visualizations.balance.status == "Needs review"
    assert "market" in result.visualizations.breakdowns
    assert "region" in result.visualizations.breakdowns


def test_explorer_missing_filter_returns_only_rows_missing_the_selected_column() -> None:
    result = DatasetExplorer().execute(
        (
            {"market": "Boston", "revenue": "100"},
            {"market": "", "revenue": "120"},
        ),
        DatasetExplorerQuery(
            filters=(
                DatasetFilter(
                    "market",
                    "is_missing",
                    "",
                ),
            ),
        ),
    )

    assert result.total_rows == 1
    assert result.rows == ({"market": "", "revenue": "120"},)


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


def test_geo_quality_uses_the_mapped_unit_column() -> None:
    rows = tuple(
        {
            **{
                key: value
                for key, value in row.items()
                if key != "market"
            },
            "geography": row["market"],
        }
        for row in clean_rows(8)
    )

    result = DataQualityAssessor().assess(
        DataQualityInput(
            rows=rows,
            estimator_type="geo_holdout",
            unit_column="geography",
        )
    )

    finding = next(
        item
        for item in result.findings
        if item.rule_id == "geo_coverage"
    )

    assert finding.passed is True
    assert finding.evidence["geographies"] == 8


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



def test_all_report_formats_include_persisted_lineage() -> None:
    lineage = {
        "input_fingerprint_sha256": "a" * 64,
        "dataset_checksum_sha256": "b" * 64,
        "estimator_type": "difference_in_differences",
        "estimator_version": "did-v2",
        "random_seed": 1729,
        "application_version": "0.1.0",
        "source_revision": "c" * 40,
        "statistical_library_versions": {
            "numpy": "2.3.1",
            "statsmodels": "0.14.5",
        },
        "estimand_snapshot": {
            "estimand_type": "average_differential_change",
            "target_outcome": "revenue",
        },
        "semantic_mapping_snapshot": {
            "outcome_column": "revenue",
        },
        "analysis_period_snapshot": {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
        },
        "analysis_selection_snapshot": {
            "selected_geographies": [],
        },
        "treatment_control_snapshot": {
            "treated_population": "yes",
        },
    }

    model = replace(
        report_model(),
        lineage=lineage,
    )

    csv_payload = CsvReportRenderer().render(model)
    pdf_payload = PdfReportRenderer().render(model)

    assert b"input_fingerprint_sha256" in csv_payload
    assert ("a" * 64).encode() in csv_payload
    assert b"estimand_snapshot" in csv_payload
    assert b"average_differential_change" in csv_payload
    assert b"source_revision" in csv_payload
    assert ("c" * 40).encode() in csv_payload

    changed_lineage = dict(lineage)
    changed_lineage["input_fingerprint_sha256"] = "f" * 64

    changed_model = replace(
        model,
        lineage=changed_lineage,
    )

    changed_pdf_payload = PdfReportRenderer().render(changed_model)

    assert pdf_payload != changed_pdf_payload
