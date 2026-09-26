# Stage 33.4.72–33.4.73 — Sync Atomic Idempotency Hardening

Status: **implemented on integration branch — runtime verification pending**

## Stage 33.4.72 — Canonical PostgreSQL Lock Identity

- PostgreSQL transaction-scoped advisory locks derive their identity from tenant, project and idempotency key.
- The identity uses length-prefixed components so delimiter-containing values cannot alias before hashing.
- Contract coverage verifies tenant/project/key separation and delimiter-safe composition.
- The SQL boundary remains parameterized through `hashtextextended` and `pg_advisory_xact_lock`.

## Stage 33.4.73 — Atomic Server Idempotency Execution

- `AtomicSyncExecutor` requires the persistence locking contract before idempotency lookup.
- Lock acquisition, lookup, delegate execution and idempotency persistence remain inside the injected transaction boundary.
- Existing matching records replay the persisted outcome without delegate re-execution.
- Reuse of the same idempotency key with a different fingerprint is rejected before delegate execution.
- SQLite persistence implements the required lock contract using transactional coordination state.
- SQLite idempotency/conflict writes no longer commit internally; transaction ownership remains with the application transaction boundary.
- The in-memory server gateway uses the atomic `execute_once` path, closing lookup-then-remember races.

## Verification boundary

- Source-level integration was inspected against the current `main` tree.
- Focused regression coverage is included for lock ordering, replay, key reuse, delimiter-safe identity and SQLite rollback/commit boundaries.
- Full GitHub Actions runtime verification remains pending because hosted Runner jobs currently terminate before exposing executable workflow steps/logs.

No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
