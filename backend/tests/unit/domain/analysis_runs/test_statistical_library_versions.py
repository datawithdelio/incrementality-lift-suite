import pytest

from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.statistical_library_versions import (
    StatisticalLibraryVersions,
)


def test_canonicalizes_statistical_library_versions_independent_of_mapping_order() -> None:
    first = StatisticalLibraryVersions.from_mapping(
        {
            "statsmodels": "0.14.5",
            "numpy": "2.3.1",
        }
    )
    second = StatisticalLibraryVersions.from_mapping(
        {
            "numpy": "2.3.1",
            "statsmodels": "0.14.5",
        }
    )

    assert first == second
    assert first.canonical_json == '{"numpy":"2.3.1","statsmodels":"0.14.5"}'
    assert first.as_dict() == {
        "numpy": "2.3.1",
        "statsmodels": "0.14.5",
    }


@pytest.mark.parametrize(
    ("versions", "message"),
    [
        ({"   ": "1.0"}, "Package name must not be blank"),
        ({"numpy": "   "}, "Package version must not be blank"),
        ({"NumPy": "2.3.1", "numpy": "2.3.1"}, "Duplicate normalized package name"),
    ],
)
def test_rejects_invalid_statistical_library_versions(
    versions: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(InvalidAnalysisRunError, match=message):
        StatisticalLibraryVersions.from_mapping(versions)
