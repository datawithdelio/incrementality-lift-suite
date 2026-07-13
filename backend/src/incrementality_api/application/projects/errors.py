class ProjectApplicationError(Exception):
    """Base exception for project application failures."""


class DuplicateProjectSlugError(ProjectApplicationError):
    """Raised when a project slug already exists in a workspace."""
