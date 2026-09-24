# Stage 33.3.6 — API Revision Propagation & Optimistic Locking Contract

## Status

**100% — revision propagation and stale-write regression coverage implemented.**

## Contract

- Resource and ResourceAssignment mutations accept an optional `expected_revision`.
- Repository contracts propagate expected revisions to persistence.
- Successful mutations expose the current revision through the API DTO.
- A stale revision is rejected with stable application conflict code `STALE_REVISION`.
- Optimistic locking is represented by a shared `OptimisticLockError` contract rather than a persistence-only application dependency.
- Existing tenant/company/project context boundaries remain intact.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics changed.

## Regression coverage

- resource revision starts at 1 and increments on update;
- stale resource update is rejected;
- assignment revision starts at 1 and increments on update;
- stale assignment update is rejected;
- API returns the current revision;
- API serializes stale writes as a stable conflict error.

## Next

Stage 33.3.7: final cross-layer integration/regression hardening.
