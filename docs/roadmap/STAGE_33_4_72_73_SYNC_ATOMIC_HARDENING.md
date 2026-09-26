# Stage 33.4.72–33.4.73 — Sync Atomic Idempotency Hardening

Status: **implemented — runtime verification pending**

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
- PostgreSQL and SQLite persistence tests cover rollback/commit and lock ordering boundaries.
- Existing client ACK/RETRY/CONFLICT/REJECTED semantics remain unchanged.

## Verification boundary

- Focused source and regression inspection completed for the changed paths.
- GitHub Actions re-run was triggered for the Python CI, PostgreSQL Sync State and PostgreSQL integration workflows.
- Current GitHub Actions attempts still terminate without executable workflow steps/logs, so runtime pass status is not claimed.

No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
