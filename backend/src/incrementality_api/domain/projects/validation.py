import re

from incrementality_api.domain.projects.errors import (
    InvalidProjectError,
)

_PROJECT_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_project_name(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise InvalidProjectError("Project name must not be blank.")

    if len(normalized) > 200:
        raise InvalidProjectError("Project name must not exceed 200 characters.")

    return normalized


def normalize_project_slug(value: str) -> str:
    normalized = value.strip().lower()

    if not normalized:
        raise InvalidProjectError("Project slug must not be blank.")

    if len(normalized) > 100:
        raise InvalidProjectError("Project slug must not exceed 100 characters.")

    if _PROJECT_SLUG_PATTERN.fullmatch(normalized) is None:
        raise InvalidProjectError(
            "Project slug must contain only lowercase letters, "
            "numbers, and single hyphens between segments."
        )

    return normalized


def normalize_project_description(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    if len(normalized) > 2000:
        raise InvalidProjectError("Project description must not exceed 2000 characters.")

    return normalized
