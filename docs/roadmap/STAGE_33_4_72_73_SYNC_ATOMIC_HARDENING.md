# Stage 33.4.72–33.4.73 — Sync Atomic Idempotency Hardening

Status: **implemented — exact-head CI/runtime verification pending**

## Stage 33.4.72
PostgreSQL transaction-scoped advisory locks derive their identity from tenant, project and idempotency key using length-prefixed components. The SQL boundary remains parameterized through `hashtextextended` and `pg_advisory_xact_lock`.

## Stage 33.4.73
- `AtomicSyncExecutor` requires the persistence locking contract before idempotency lookup.
- Lock, lookup, delegate execution and idempotency persistence remain inside the injected transaction.
- Matching records replay the persisted outcome without delegate re-execution.
- Idempotency-key reuse with a different fingerprint is rejected before delegate execution.
- SQLite implements the lock contract with transactional coordination state and leaves commit/rollback to the injected transaction boundary.
- PostgreSQL, SQLite and in-memory gateway tests cover the atomic path.

## Verification boundary
The release gate remains pending until the exact merged head has successful CI and, where configured, real PostgreSQL-backed runtime verification.

No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
