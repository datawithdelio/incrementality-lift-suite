import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self

from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError

_PACKAGE_SEPARATOR_PATTERN = re.compile(r"[-_.]+")


@dataclass(frozen=True, slots=True)
class StatisticalLibraryVersions:
    """Immutable, canonical versions of libraries that affect an estimate."""

    _items: tuple[tuple[str, str], ...]

    @classmethod
    def from_mapping(cls, versions: Mapping[str, str]) -> Self:
        if not versions:
            raise InvalidAnalysisRunError(
                "Statistical library versions must not be empty."
            )

        normalized: dict[str, str] = {}
        for package_name, package_version in versions.items():
            name = cls._normalize_package_name(package_name)
            if name in normalized:
                raise InvalidAnalysisRunError(
                    f"Duplicate normalized package name '{name}'."
                )
            if not package_version.strip():
                raise InvalidAnalysisRunError(
                    f"Package version must not be blank for '{name}'."
                )
            normalized[name] = package_version

        return cls(tuple(sorted(normalized.items())))

    @classmethod
    def from_json(cls, serialized: str) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError(
                "Statistical library versions must not be blank."
            )
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError(
                "Statistical library versions must be valid JSON."
            ) from error
        if not isinstance(parsed, dict) or not all(
            isinstance(name, str) and isinstance(version, str)
            for name, version in parsed.items()
        ):
            raise InvalidAnalysisRunError(
                "Statistical library versions must be a JSON object of strings."
            )
        return cls.from_mapping(parsed)

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            dict(self._items),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def as_dict(self) -> dict[str, str]:
        return dict(self._items)

    @staticmethod
    def _normalize_package_name(package_name: str) -> str:
        stripped = package_name.strip()
        if not stripped:
            raise InvalidAnalysisRunError("Package name must not be blank.")
        return _PACKAGE_SEPARATOR_PATTERN.sub("-", stripped).lower()
