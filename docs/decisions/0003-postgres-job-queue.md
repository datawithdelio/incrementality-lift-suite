# ADR 0003: PostgreSQL Durable Job Queue

## Decision

Use a PostgreSQL-backed job queue initially.

## Required behavior

- Atomic job claiming
- Worker leases
- Heartbeats
- Retries
- Dead-letter handling
- Cancellation
- Idempotency

Kafka or a dedicated broker will be considered only when justified by scale.
