class ProjectDomainError(Exception):
    """Base exception for project-domain failures."""


class InvalidProjectError(ProjectDomainError):
    """Raised when project data violates domain rules."""
