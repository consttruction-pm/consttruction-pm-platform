# Job-Step Transaction & Replay Boundary

## Scope

This boundary defines the application contract for a multi-step job: `Job -> Step 1 -> Step 2 -> Step 3 -> Commit`.

It does not contain Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar or financial calculations.

## State contract

The versioned state set is:
- `PENDING`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`
- `RETRYABLE`
- `ROLLED_BACK`
- `REPLAYED`
- `CONFLICT`

## Transaction semantics

1. Idempotency locking, lookup, step execution and success persistence occur inside the application transaction.
2. A step failure aborts the business transaction; the authoritative job state becomes `ROLLED_BACK` in a separate failure-record transaction.
3. Retryable failures return `RETRYABLE`; callers retry with a new idempotency key while preserving the expected revision.
4. Non-retryable failures return `FAILED`; replaying the same idempotency key returns `REPLAYED` without executing steps again.
5. A matching idempotency key with a different canonical payload returns `JOB_IDEMPOTENCY_KEY_REUSE`.
6. An optimistic revision mismatch returns `CONFLICT` and no step executes.
7. Same-key concurrent execution is serialized by the repository idempotency lock; only one execution performs the steps.

## Verification

Focused integration coverage is in `tests/integration/test_job_step_transaction.py` and covers success/order, Step-2 failure, rollback, retry, replay, idempotency-key conflict, optimistic-lock mismatch, non-retryable failure and same-key concurrency.

The boundary is intentionally persistence-adapter-neutral. A production PostgreSQL adapter must bind the same contract to the existing application transaction and idempotency primitives rather than introduce a second transaction model.

## Runtime evidence

- PR #206 merged on 2026-09-27 with merge SHA `9ffc63f80612b110cc4a720d90a2c79789efe273`.
- Exact-head ConstructionPM CI run #1084 succeeded across Python 3.11, 3.12 and 3.13; Python 3.11 reported `679 passed, 9 skipped`.
- Exact-head Client Typecheck run #787 succeeded for Web, Desktop, Mobile and client-sync.
- The job boundary remains persistence-adapter-neutral; live PostgreSQL verification is covered by the existing PostgreSQL adapter gates rather than by this reference boundary.
- Next action: proceed to Daily Task Queue #202 item 4 (API/Web-readiness regression), then item 5 documentation reconciliation.
