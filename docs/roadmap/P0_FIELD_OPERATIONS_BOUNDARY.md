# P0 Field Operations Boundary

Version: v1

This boundary owns the Application/API persistence contract for field operations: daily logs, issues, observations, inspections, quality, safety, punch and photo records.

## Invariants

- Every resource is tenant- and project-scoped.
- Revision is explicit and optimistic-lock validation occurs before write.
- Replayed idempotency keys return the existing resource without appending another audit event.
- Reuse of an idempotency key with a different resource fingerprint is rejected.
- Audit records are append-only.
- Payload is opaque to this boundary; no scheduling, progress, EVM, resource/cost or financial calculation is performed.
- Location is represented as an opaque location_ref; geospatial semantics remain outside this module.
- External storage/photo providers must be connected through adapters; this boundary does not select a vendor.

## PostgreSQL persistence

PostgreSQL persistence and transaction integration are implemented on current main. The adapter reuses the platform transaction/idempotency primitives; the boundary does not create a second transaction model.

Remaining work is runtime verification and regression maintenance: execute the live PostgreSQL gate against the current main head, keep tenant/project/revision/idempotency/audit invariants covered, and record any reproducible defect before changing the persistence contract.
