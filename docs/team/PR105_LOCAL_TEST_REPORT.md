# PR #105 — Local Test Report

Commit under test: 6309fca58120e645a7eff202cd68aeb91902c5f4

## Executed locally

A minimal isolated regression reproducing the transaction-scoped idempotency-lock behavior was executed with pytest:

- Result: **1 passed**
- Test: same idempotency key executes the delegate exactly once under concurrent submissions.

## PostgreSQL live test

The repository test `tests/integration/test_postgres_idempotency_lock_live.py` requires:

- Python package `psycopg`
- `CONSTRUCTION_PM_POSTGRES_DSN`

Neither is available in this ChatGPT execution environment:

- `psycopg`: unavailable
- `psycopg2`: unavailable
- `CONSTRUCTION_PM_POSTGRES_DSN`: not configured
- `psql`: unavailable

Therefore the live PostgreSQL regression was **not claimed as executed**.

## Scope

The only repository change in PR #105 remains test hardening:

- idempotency keys are generated uniquely per test execution;
- mutation identity is asserted in the same-key concurrency regression.

The production atomic-lock implementation was not changed.

## Remaining verification

When PostgreSQL/CI infrastructure is available, run the live integration test and then the normal GitHub Actions PostgreSQL workflow. Stage 33.4.71 must remain runtime-pending until that real test executes successfully.
