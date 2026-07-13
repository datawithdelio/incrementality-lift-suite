import re

from incrementality_api.domain.tenancy.errors import TenancyDomainError

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_name(
    value: str,
    *,
    field_name: str,
    error_type: type[TenancyDomainError],
) -> str:
    normalized = " ".join(value.split())

    if not normalized:
        raise error_type(f"{field_name} cannot be blank.")

    return normalized


def normalize_slug(
    value: str,
    *,
    error_type: type[TenancyDomainError],
) -> str:
    normalized = value.strip().lower()

    if not normalized:
        raise error_type("Slug cannot be blank.")

    if not _SLUG_PATTERN.fullmatch(normalized):
        raise error_type("Slug must contain lowercase letters, numbers, and hyphens only.")

    return normalized


def normalize_email(
    value: str,
    *,
    error_type: type[TenancyDomainError],
) -> str:
    normalized = value.strip().lower()

    if not _EMAIL_PATTERN.fullmatch(normalized):
        raise error_type("A valid email address is required.")

    return normalized
