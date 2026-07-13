# Event Processing

The first version uses PostgreSQL transactional outbox events.

An application transaction may atomically create:

1. A domain record
2. A durable job
3. An outbox event

Kafka may be introduced later when event volume or independent consumers
justify the added operational complexity.
