from uuid import uuid4

from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.infrastructure.database.repositories.dataset_columns import (
    to_dataset_column_model,
    to_dataset_column_profile,
)


def test_round_trips_dataset_column_profile() -> None:
    dataset_id = uuid4()

    profile = DatasetColumnProfile(
        ordinal_position=2,
        source_name="Campaign Revenue",
        normalized_name="campaign_revenue",
        inferred_type=DatasetColumnType.FLOAT,
        nullable=True,
        missing_count=3,
    )

    model = to_dataset_column_model(
        dataset_id=dataset_id,
        profile=profile,
    )

    assert model.dataset_id == dataset_id
    assert model.ordinal_position == 2
    assert model.source_name == "Campaign Revenue"
    assert model.normalized_name == "campaign_revenue"
    assert model.inferred_type == "float"
    assert model.nullable is True
    assert model.missing_count == 3

    assert to_dataset_column_profile(model) == profile
