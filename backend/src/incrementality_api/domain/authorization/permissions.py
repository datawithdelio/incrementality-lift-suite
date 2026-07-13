from enum import StrEnum


class WorkspacePermission(StrEnum):
    VIEW_WORKSPACE = "view_workspace"
    MANAGE_WORKSPACE = "manage_workspace"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_PROJECTS = "manage_projects"
    MANAGE_DATASETS = "manage_datasets"
    RUN_ANALYSES = "run_analyses"
    VIEW_REPORTS = "view_reports"
