# P0 Live PostgreSQL Integration Gate

This gate executes the production PostgreSQL persistence paths for the Hasan P0 backend boundaries in the repository's PostgreSQL 16 CI service.

## Covered

- Dependency Graph:
  - real PostgreSQL schema initialization;
  - revision/audit round-trip;
  - idempotent replay and key-reuse rejection;
  - stale revision rejection;
  - transaction rollback;
  - concurrent revision serialization.
- Field Operations:
  - real PostgreSQL schema initialization;
  - revision/resource round-trip;
  - idempotent replay;
  - stale revision rejection;
  - idempotency-key reuse rejection;
  - transaction rollback.

The existing Application transaction boundary remains authoritative. These repositories do not create a competing transaction boundary.

## Boundary

No scheduling/P6, calendar, duration, Progress/EVM, Resource/Cost or financial formulas are introduced. PostgreSQL is persistence infrastructure behind the existing application contracts.

The workflow is triggered for changes to the covered persistence modules and live integration tests, in addition to manual dispatch.
