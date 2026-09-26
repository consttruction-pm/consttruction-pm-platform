# Stage 34.2.11 — Portfolio Control Action Audit Ledger

Status: implementation in progress.

## Scope

Add an append-only audit ledger to the existing Portfolio Control Action persistence boundary.

## Acceptance criteria

- Every persisted Portfolio Control Action transition writes one audit event in the same database transaction.
- Audit events are scoped by tenant, portfolio, action and portfolio revision.
- Audit events are append-only and uniquely revisioned per action.
- Audit history is queryable in ascending revision order.
- Audit events preserve actor and timezone-aware occurrence timestamp.
- Audit events preserve an immutable action snapshot.
- Idempotent replay does not append duplicate audit events.
- Existing revision/idempotency semantics remain unchanged.
- PostgreSQL/transaction runtime verification is required before merge.

## Non-goals

- No new Portfolio Action business semantics.
- No automatic project mutation.
- No P6/Scheduling, Progress/EVM, Resource/Cost or financial calculation.
