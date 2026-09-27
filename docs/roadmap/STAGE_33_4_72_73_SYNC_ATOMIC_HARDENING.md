# Stage 33.4.72–33.4.73 — Sync Atomic Idempotency Hardening

Status: **100% — runtime-verified 2026-09-27 through PR #171**

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
Runtime verification is complete for PR #171 head `93d1a3b620a68a8a55e0fe1e504a2bac41b17139`.

- ConstructionPM CI run **36296471378** succeeded.
- Client Typecheck run **36296471377** succeeded.
- PostgreSQL Sync State Integration run **36296471403** succeeded; its live `postgres-sync` job completed the configured live sync-state tests.
- PostgreSQL Integration run **36296471450** succeeded; its `postgres` job ran `tests/integration/test_postgres_*.py` and `tests/integration/test_portfolio_decision_postgres_live.py` with **16 passed**.
- The PostgreSQL service was a real PostgreSQL 16 container in GitHub Actions, so this is runtime evidence rather than source inspection.

No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
