# Stage 33.4 — SQLite Transaction Boundary Hardening

## Status

**100% — transaction-boundary regression hardening implemented.**

## Scope

- Reconciles the application transaction contract with the SQLite transaction adapter.
- Verifies rollback of a Resource persistence mutation when the application transaction fails.
- Verifies nested repository transaction scopes participate in the existing application transaction instead of committing independently.
- Fixes the stable STALE_REVISION application error mapping import.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics changed.

## Architectural rule

The Application layer owns the transaction boundary. SQLite persistence participates in an existing transaction and does not commit independently when an outer application transaction is active.

## Next

Continue with the next unfinished Stage 33 backend/platform hardening item documented in the repository.
