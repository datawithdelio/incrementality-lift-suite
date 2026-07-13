# Source of Truth

## Authoritative state

PostgreSQL owns:

- Users
- Organizations
- Workspaces
- Projects
- Dataset metadata
- Dataset versions
- Analysis runs
- Jobs
- Results
- Reports
- Events
- Audit records

## Object storage

S3 or MinIO owns large binary objects:

- Uploaded datasets
- Parquet files
- Model artifacts
- Generated charts
- Exported reports

## Redis

Redis contains replaceable or temporary data only:

- Cache entries
- Rate limits
- Temporary locks
- Short-lived progress data
