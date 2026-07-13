from uuid import UUID


class DatasetObjectKeyBuilder:
    """Build deterministic project-scoped object keys."""

    def build(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        source_filename: str,
        checksum_sha256: str,
    ) -> str:
        return (
            f"workspaces/{workspace_id}/"
            f"projects/{project_id}/"
            f"datasets/{checksum_sha256}/"
            f"{source_filename}"
        )
