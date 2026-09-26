# PR #105 — Local Test Report

Commit under test: `fdec89cd5ab5f7f4a538909f2d2998de01681942`

## ChatGPT environment verification

The relevant Stage 33.4.71 files from PR #105 were reconstructed in an isolated ChatGPT workspace and the bounded local verification was run there.

Environment checks:
- `pytest 9.0.2`: available
- Python 3.13.5: available
- `psycopg`: unavailable
- `psycopg2`: unavailable
- `psql`: unavailable
- PostgreSQL server binaries: unavailable
- `CONSTRUCTION_PM_POSTGRES_DSN`: unavailable
- external package installation: unavailable because this execution environment has no network/DNS access

## Test results

### Repository live PostgreSQL integration test

Test: `tests/integration/test_postgres_idempotency_lock_live.py`

Result in ChatGPT environment: **1 skipped**.

Reason: the test uses `pytest.importorskip("psycopg")`, and `psycopg` is unavailable. A live PostgreSQL DSN/server is also unavailable in this environment.

Therefore this result is **not** PostgreSQL runtime verification.

### Deterministic local concurrency regression

A local test double was used against the reconstructed production `AtomicSyncExecutor` control flow to verify the bounded concurrency behavior without pretending it is PostgreSQL.

Result: **6 passed in 0.04s**

- same idempotency key: concurrent submissions execute the delegate exactly once and replay the saved outcome;
- distinct idempotency keys: concurrent submissions execute independently;
- idempotency-key reuse with a different mutation is rejected;
- the PostgreSQL lock SQL is checked to use `pg_advisory_xact_lock(hashtextextended(...))`;
- the lock key is checked to include tenant, project, and idempotency key;\n- structured lock-key encoding prevents delimiter-based scope ambiguity (for example values containing `|`).

This simulation is **not claimed as PostgreSQL runtime verification**. It checks the test logic and atomic/idempotency control flow only.

## GitHub Actions status

The current head has associated workflow runs, but the GitHub Actions jobs did not reach executable steps:

- PostgreSQL Integration run `36219818970`: failure; job `postgres` has `steps: null`.
- PostgreSQL Sync State Integration run `36219818977`: failure; job `postgres-sync` has `steps: null`.
- ConstructionPM CI run `36219818988`: all three Python test jobs failed with `steps: null`.
- Client Typecheck run `36219818949`: all four typecheck jobs failed with `steps: null`.

Because no executable job steps were exposed, these failures are classified as **CI/runner infrastructure failures**, not test failures. No CI success is inferred from them, and the workflow is not being repeatedly rerun solely to chase the same infrastructure condition.

## Scope

The production implementation was hardened after local validation: PostgreSQL advisory-lock scope now uses deterministic JSON-array encoding of `(tenant_id, project_id, idempotency_key)` instead of delimiter concatenation. This preserves tenant/project/key scoping without ambiguous `|`-based composite encoding.

PR #105 remains a bounded Stage 33.4.71 verification/hardening change:
- idempotency keys are unique per test execution;
- the same-key test asserts the replayed mutation identity;
- PostgreSQL idempotency execution is protected by the transaction-scoped advisory lock;\n- advisory-lock key encoding is now unambiguous for delimiter-containing identifiers.

## Current gate

Stage 33.4.71 remains **runtime verification pending**.

The remaining external gate is a real PostgreSQL integration execution on an operational runner. The local 2-pass concurrency simulation and the skipped live test are supporting evidence only; they do not replace that gate.

`docs/roadmap/STAGE_STATUS.md` must not be marked runtime-verified until the real PostgreSQL test executes and passes.
