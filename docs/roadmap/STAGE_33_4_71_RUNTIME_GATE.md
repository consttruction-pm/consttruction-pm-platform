# Stage 33.4.71 — PostgreSQL Atomic Idempotency Execution Lock

Status: implemented — runtime verification pending.

- PostgreSQL idempotency execution acquires a transaction-scoped advisory lock derived from tenant/project/idempotency-key identity before delegate execution.
- The live PostgreSQL regression covers two independent connections using the same idempotency key and requires exactly one delegate execution.
- A focused persistence-contract regression verifies the adapter emits `pg_advisory_xact_lock` using the composite mutation identity.
- Existing database uniqueness and fingerprint checks remain in place.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
- Runtime CI is not claimed: the latest commits currently report no associated executable workflow runs.
