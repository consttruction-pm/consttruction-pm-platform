# Stage 33.4.58 — PostgreSQL Persistence Adapter

A PostgreSQL-specific persistence adapter now implements the same sync-state semantics as SQLite.

## Guarantees

- tenant/project/idempotency-key uniqueness is database-enforced;
- tenant/project/mutation-id conflict uniqueness is database-enforced;
- SQL parameters are bound rather than interpolated;
- persistence remains outside Scheduling/P6 and other business calculations.

## Important limitation

The adapter is PostgreSQL-compatible code behind a narrow connection protocol. This repository stage does not claim a live PostgreSQL server was provisioned or that concurrent database tests have executed against one.

A live database CI environment and race-condition tests remain a production verification gate.
