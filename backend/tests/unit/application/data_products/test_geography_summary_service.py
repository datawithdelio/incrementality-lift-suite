from dataclasses import dataclass
from uuid import uuid4

import pytest

from incrementality_api.application.data_products.services import (
    DatasetProductQuery,
    ProductionDataProducts,
)
from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)


@dataclass(frozen=True)
class Mapping:
    version: int = 4
    unit_column: str = "geography"
    outcome_column: str = "conversions"
    spend_column: str | None = "ad_spend"
    covariate_columns: tuple[str, ...] = (
        "sessions",
        "revenue",
    )


class SummaryService(ProductionDataProducts):
    def __init__(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        mapping: Mapping | None,
    ) -> None:
        super().__init__(
            unit_of_work=object(),
            object_storage=object(),
            quality_writer=object(),
        )  # type: ignore[arg-type]

        self.loaded_rows = rows
        self.loaded_mapping = mapping

    async def _load(
        self,
        scope: DatasetProductQuery,
    ) -> tuple[
        tuple[dict[str, str], ...],
        Mapping | None,
    ]:
        del scope

        return (
            self.loaded_rows,
            self.loaded_mapping,
        )


async def test_service_builds_summary_from_all_loaded_rows() -> None:
    rows = tuple(
        {
            "geography": (
                "Newark"
                if index < 60
                else "Elizabeth"
            ),
            "conversions": "2",
            "ad_spend": "5",
            "sessions": "20",
            "revenue": "30",
            "latitude": (
                "40.7357"
                if index < 60
                else "40.6639"
            ),
            "longitude": (
                "-74.1724"
                if index < 60
                else "-74.2107"
            ),
        }
        for index in range(125)
    )

    service = SummaryService(
        rows=rows,
        mapping=Mapping(),
    )

    result = await service.geography_summary(
        DatasetProductQuery(
            uuid4(),
            uuid4(),
            uuid4(),
        )
    )

    assert result.mapping_version == 4
    assert result.total_geographies == 2

    by_name = {
        item.value: item
        for item in result.geographies
    }

    assert (
        by_name["Newark"]
        .observation_count
        == 60
    )

    assert (
        by_name["Elizabeth"]
        .observation_count
        == 65
    )

    assert (
        by_name["Newark"]
        .metrics
        .outcome_sum
        == 120
    )

    assert (
        by_name["Elizabeth"]
        .metrics
        .spend_sum
        == 325
    )


async def test_service_requires_saved_semantic_mapping() -> None:
    service = SummaryService(
        rows=(
            {
                "geography": "Newark",
                "conversions": "10",
            },
        ),
        mapping=None,
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="semantic mapping",
    ):
        await service.geography_summary(
            DatasetProductQuery(
                uuid4(),
                uuid4(),
                uuid4(),
            )
        )
