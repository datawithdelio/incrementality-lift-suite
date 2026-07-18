class ProjectApplicationError(Exception):
    """Base exception for project application failures."""


class DuplicateProjectSlugError(ProjectApplicationError):
    """Raised when a project slug already exists in a workspace."""


class ProjectUnavailableError(ProjectApplicationError):
    """Raised when a project is missing or outside the requested workspace."""
