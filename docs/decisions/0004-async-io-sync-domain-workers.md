# ADR 0004: Async I/O, Synchronous Domain Logic, and Workers

## Decision

Use three execution styles based on the type of work.

### Async I/O

Use asynchronous functions for:

- PostgreSQL access
- Object-storage access
- External HTTP calls
- Network communication
- Upload and download streams

### Synchronous domain logic

Use normal Python functions for:

- Business rules
- Validation
- Lift calculations
- Date-window rules
- Pure transformations

### Separate workers

Use separate worker processes for:

- Statistical estimation
- Bootstrap procedures
- Synthetic-control optimization
- Bayesian sampling
- Large dataframe transformations
- Placebo and sensitivity analyses

## Reason

Async improves concurrency while waiting for I/O. It does not make
CPU-intensive statistical computation faster. Heavy computation must not
block API request processing.
