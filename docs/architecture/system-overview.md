# System Overview

The application begins as a modular monolith.

## Main components

1. Next.js frontend
2. FastAPI API
3. PostgreSQL source of truth
4. Redis cache and rate limiter
5. MinIO or S3 object storage
6. Separate Python worker processes
7. PostgreSQL durable job queue
8. Transactional outbox
9. Monitoring and operational tooling

CPU-intensive statistical work must not execute inside HTTP requests.
