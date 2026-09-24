# Stage 33.1 — Backend Concurrency Hardening

## Scope

Stage 33 starts with backend/platform hardening within Developer 1 ownership. This substage strengthens Resource & Cost persistence without changing shared Scheduling, Progress/EVM, or calculation semantics.

## Completed

- Added optimistic-locking revision semantics to resource_assignments.
- Added schema migration from Resource schema version 2 to version 3.
- Preserved existing Resource optimistic locking.
- Added assignment revision lookup for application/integration layers.
- Added stale-update rejection tests.
- Added unconditional upsert revision increment regression coverage.
- Added legacy-schema migration coverage.
- Kept Decimal persistence as exact text and transaction boundaries explicit.

## Contract

save_assignment(..., expected_revision=N) updates an assignment only when its current revision is N, then increments the revision. A stale revision raises OptimisticLockError.

Unconditional assignment upsert remains supported for existing callers and increments the revision on an existing assignment.

## Boundary

This substage does not alter Scheduling/P6 semantics, Progress/EVM core semantics, or Shared Calculation Core formulas. Assignment concurrency is persistence infrastructure behavior.

## Next

Stage 33.2 should continue with cross-module integration/portability checks that remain inside Developer 1's backend/database/integration-support scope.
