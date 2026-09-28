# P6 Activity Period Actual Persistence v1

This boundary persists P6 activity-period actual data only.

## Scope
- tenant/project/project_revision scoped
- immutable actual identity (tenant_id, project_id, actual_id)
- typed Decimal storage for actual units and actual cost
- explicit unit/currency metadata
- deterministic listing by activity, period and actual id
- stale revision rejection and identical replay idempotency
- SQLite and PostgreSQL repository boundaries
- application-owned transaction boundary

## Semantic boundary
This module does not calculate earned value, cost, rates, period performance, scheduling, calendars, duration or resource semantics. Shared Core remains authoritative for those meanings.

## Evidence
- focused SQLite regression coverage
- live PostgreSQL round-trip, isolation, revision and rollback coverage
- PostgreSQL integration workflow trigger included
